import collections
import dataclasses
import math
import os
import requests
import sqlite3
import typing

from airq.cache import cache
from airq.providers.base import Metrics, Provider, ProviderOutOfService, ProviderType


def haversine_distance(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    """
    Calculate the great circle distance between two points 
    on the earth (specified in decimal degrees)
    """
    # convert decimal degrees to radians
    lon1, lat1, lon2, lat2 = map(math.radians, [lon1, lat1, lon2, lat2])

    # haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.asin(math.sqrt(a))
    r = 6371  # Radius of earth in kilometers. Use 3956 for miles
    return c * r


@dataclasses.dataclass(frozen=True)
class Sqlite3Zipcode:
    id: int
    zipcode: str
    latitude: float
    longitude: float
    geohash: typing.List[str]

    def __hash__(self) -> int:
        return hash(self.id)

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "Sqlite3Zipcode":
        return cls(
            id=row["ID"],
            zipcode=row["zipcode"],
            latitude=row["latitude"],
            longitude=row["longitude"],
            geohash=[row[f"geohash_bit_{i + 1}"] for i in range(12)],
        )


@dataclasses.dataclass(frozen=True)
class Sensor:
    id: int
    distance: float
    pm_25: float


class PurpleairProvider(Provider):
    TYPE = ProviderType.PURPLEAIR
    MAX_RADIUS = 25
    MAX_SENSORS = 10
    DB_PATH = "airq/providers/purpleair.db"

    def _check_database(self):
        if not os.path.exists(self.DB_PATH):
            cwd = os.getcwd()
            contents = os.listdir(cwd)
            msg = (
                f"Database unexecpectedly absent at {self.DB_PATH}"
                f"(cwd: {cwd}, contents: {listdir})"
            )
            raise ProviderOutOfService(msg)

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect("airq/providers/purpleair.db")
        conn.row_factory = sqlite3.Row
        return conn

    @cache.memoize()
    def _find_neighboring_sensors(
        self, zipcode: Sqlite3Zipcode
    ) -> "collections.OrderedDict[int, float]":  # See https://stackoverflow.com/a/52626233
        self.logger.info("Finding nearby sensors for %s", zipcode)
        conn = self._get_connection()
        cursor = conn.cursor()
        gh = list(zipcode.geohash)
        distances: "collections.OrderedDict[int, float]" = collections.OrderedDict()
        while gh:
            sql = "SELECT id, latitude, longitude FROM sensors WHERE {}".format(
                " AND ".join([f"geohash_bit_{i}=?" for i in range(1, len(gh) + 1)])
            )
            cursor.execute(sql, tuple(gh))
            rows = cursor.fetchall()
            if rows:
                # We will sort the sensors by distance and add them until we have MAX_SENSORS
                # sensors. As soon as we see a sensor further away than MAX_RADIUS, we're done.
                sensors = sorted(
                    [
                        (
                            row["id"],
                            haversine_distance(
                                zipcode.longitude,
                                zipcode.latitude,
                                row["longitude"],
                                row["latitude"],
                            ),
                        )
                        for row in rows
                        if row["id"] not in distances
                    ],
                    key=lambda t: t[1],
                )
                while sensors:
                    sensor_id, distance = sensors.pop()
                    if distance > self.MAX_RADIUS:
                        return distances
                    distances[sensor_id] = distance
                    if len(distances) >= self.MAX_SENSORS:
                        return distances
            gh.pop()
        return distances

    def _get_sensors_for_zipcode(self, zipcode: str) -> typing.List[Sensor]:
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM zipcodes WHERE zipcode=?", (zipcode,))
        row = cursor.fetchone()
        conn.close()
        if not row:
            return []

        # Now get the closest sensors
        sqlite3_zip = Sqlite3Zipcode.from_row(row)
        distances = self._find_neighboring_sensors(sqlite3_zip)
        if not distances:
            return []

        try:
            resp = requests.get(
                "https://www.purpleair.com/json?show={}".format(
                    "|".join(map(str, distances.keys()))
                )
            )
        except requests.RequestException as e:
            raise ProviderOutOfService(
                "Error retrieving data for sensors {} and zipcode {}: {}".format(
                    ", ".join(map(str, distances.keys())), zipcode, e,
                )
            )
        else:
            sensors = []
            missing_ids = set(distances.keys())
            for r in resp.json().get("results"):
                if not r.get("ParentID"):
                    pm_25 = float(r.get("PM2_5Value", 0))
                    if 0 < pm_25 < 500:
                        distance = distances.get(r["ID"])
                        if distance is None:
                            self.logger.warning(
                                "Mismatch: sensor %s has no corresponding distance",
                                r["ID"],
                            )
                        else:
                            missing_ids.discard(r["ID"])
                            sensors.append(Sensor(r["ID"], distance, pm_25))
            if missing_ids:
                self.logger.warning("No results for ids: %s", missing_ids)
            return sorted(sensors, key=lambda s: s.pm_25)

    def get_metrics(self, zipcode: str) -> typing.Optional[Metrics]:
        self._check_database()

        sensors = self._get_sensors_for_zipcode(zipcode)
        if not sensors:
            return None

        average_pm_25 = round(sum(s.pm_25 for s in sensors) / len(sensors), ndigits=3)
        max_sensor_distance = sensors[-1].distance

        return self._generate_metrics(
            [
                ("Average pm25", average_pm_25),
                ("Sensor IDs", ", ".join([str(s.id) for s in sensors])),
                ("Max sensor distance", f"{max_sensor_distance}km"),
            ],
            zipcode,
        )
