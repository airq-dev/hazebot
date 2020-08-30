import dataclasses
import math
import requests
import sqlite3
import typing

from airq.cache import cache
from airq.providers.base import Metrics, Provider, ProviderType


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


class PurpleairProvider(Provider):
    TYPE = ProviderType.PURPLEAIR
    RADIUS = 5

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect("airq/providers/purpleair.db")
        conn.row_factory = sqlite3.Row
        return conn

    @cache.memoize()
    def _find_neighboring_sensor_ids(self, zipcode: Sqlite3Zipcode) -> typing.Set[int]:
        self.logger.info("Finding nearby sensors for %s", zipcode)
        conn = self._get_connection()
        cursor = conn.cursor()
        gh = list(zipcode.geohash)
        sensor_ids: typing.Set[int] = set()
        while gh:
            sql = "SELECT id, latitude, longitude FROM sensors WHERE {}".format(
                " AND ".join([f"geohash_bit_{i}=?" for i in range(1, len(gh) + 1)])
            )
            cursor.execute(sql, tuple(gh))
            rows = cursor.fetchall()
            if rows:
                # Add all sensors within the allowed radius.
                # If there are none, we've gone too far and can stop.
                should_continue = False
                for row in rows:
                    # If we haven't seen this sensor before, check if it's within the radius.
                    if (
                        row["id"] not in sensor_ids
                        and haversine_distance(
                            zipcode.longitude,
                            zipcode.latitude,
                            row["longitude"],
                            row["latitude"],
                        )
                        <= self.RADIUS
                    ):
                        sensor_ids.add(row["id"])
                        should_continue = True
                if not should_continue:
                    break
            gh.pop()
        return sensor_ids

    def _get_sensors_for_zipcode(self, zipcode: str) -> typing.List[dict]:
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM zipcodes WHERE zipcode=?", (zipcode,))
        row = cursor.fetchone()
        conn.close()
        if not row:
            return []

        # Now get the closest sensors
        sqlite3_zip = Sqlite3Zipcode.from_row(row)
        sensor_ids = self._find_neighboring_sensor_ids(sqlite3_zip)
        if not sensor_ids:
            return []

        try:
            resp = requests.get(
                "https://www.purpleair.com/json?show={}".format(
                    "|".join(map(str, sensor_ids))
                )
            )
        except requests.RequestException as e:
            self.logger.exception(
                "Error retrieving data for sensors %s and zipcode %s: %s",
                ", ".join(map(str, sensor_ids)),
                zipcode,
                e,
            )
            return []
        else:
            return [
                s
                for s in resp.json().get("results")
                # Less than 0 or greater than 500 is, we hope, some kind of fluke.
                # I've seen it in the data...
                if 0 < float(s.get("PM2_5Value", 0)) < 500
            ]

    def get_metrics(self, zipcode: str) -> typing.Optional[Metrics]:
        sensors = self._get_sensors_for_zipcode(zipcode)
        if not sensors:
            return None

        average_pm_25 = round(
            sum(float(s["PM2_5Value"]) for s in sensors) / len(sensors), ndigits=3
        )

        return self._generate_metrics(
            [
                ("Average pm25", average_pm_25),
                ("Sensor IDs", ", ".join([str(s["ID"]) for s in sensors])),
                ("Radius", f"{self.RADIUS}km"),
            ],
            zipcode,
        )
