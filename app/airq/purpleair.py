import collections
import dataclasses
import logging
import os
import requests
import sqlite3
import typing

from airq import util
from airq.cache import cache


logger = logging.getLogger(__name__)


@dataclasses.dataclass(frozen=True)
class Metrics:
    pm25: float
    num_sensors: int
    max_sensor_distance: float

    @property
    def pm25_display(self) -> str:
        return util.get_pm25_display(self.pm25)


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
    pm25: float


class PurpleairProvider:
    MAX_RADIUS = 25
    MAX_SENSORS = 10
    DB_PATH = "airq/purpleair.db"

    def __repr__(self):
        return f"{self.__class__.__name__}()"

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
        conn = sqlite3.connect(self.DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn

    @cache.memoize()
    def _find_neighboring_sensors(
        self, zipcode: Sqlite3Zipcode
    ) -> "collections.OrderedDict[int, float]":  # See https://stackoverflow.com/a/52626233
        logger.info("Finding nearby sensors for %s", zipcode)
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
                            util.haversine_distance(
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

    @staticmethod
    def _make_purpleair_pm25_key(sensor_id: int) -> str:
        return f"purpleair-pm25-sensor-{sensor_id}"

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

        sensors = []
        for sensor_id in list(distances):
            pm25 = cache.get(self._make_purpleair_pm25_key(sensor_id))
            if pm25:
                sensors.append(Sensor(sensor_id, pm25, distances[sensor_id]))
                del distances[sensor_id]

        if distances:
            logger.info(
                "Retrieving pm25 data from purpleair for %s sensors", len(distances)
            )
            try:
                resp = requests.get(
                    "https://www.purpleair.com/json?show={}".format(
                        "|".join(map(str, distances.keys()))
                    )
                )
            except requests.RequestException as e:
                logger.exception(
                    "Error retrieving data for sensors %s and zipcode %s: %s",
                    ", ".join(map(str, distances.keys())),
                    zipcode,
                    e,
                )
            else:
                missing_ids = set(distances.keys())
                for r in resp.json().get("results"):
                    if not r.get("ParentID"):
                        pm25 = float(r.get("PM2_5Value", 0))
                        if 0 < pm25 < 500:
                            distance = distances.get(r["ID"])
                            if distance is None:
                                logger.warning(
                                    "Mismatch: sensor %s has no corresponding distance",
                                    r["ID"],
                                )
                            else:
                                missing_ids.discard(r["ID"])
                                cache.set(
                                    self._make_purpleair_pm25_key(r["ID"]),
                                    pm25,
                                    timeout=60 * 10,
                                )  # 10 minutes
                                sensors.append(Sensor(r["ID"], distance, pm25))
                if missing_ids:
                    logger.warning("No results for ids: %s", missing_ids)

        return sorted(sensors, key=lambda s: s.distance)

    def get_metrics(self, zipcode: str) -> typing.Optional[Metrics]:
        self._check_database()

        sensors = self._get_sensors_for_zipcode(zipcode)
        if not sensors:
            return None

        average_pm25 = round(sum(s.pm25 for s in sensors) / len(sensors), ndigits=3)
        aqi_display = util.get_pm25_display(average_pm25)

        return Metrics(
            pm25=average_pm25,
            num_sensors=len(sensors),
            max_sensor_distance=round(sensors[-1].distance, ndigits=3),
        )


PURPLEAIR_PROVIDER = PurpleairProvider()
