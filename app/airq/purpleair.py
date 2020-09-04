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
    readings: typing.List[float]

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

    def _refresh_sensor_distances(
        self, zipcode: Sqlite3Zipcode, exclude: typing.Set[int], num_desired: int
    ) -> "collections.OrderedDict[int, float]":  # See https://stackoverflow.com/a/52626233
        logger.info(
            "Refreshing sensor coordinates for %s for %s sensors",
            zipcode.zipcode,
            num_desired,
        )
        conn = self._get_connection()
        cursor = conn.cursor()
        gh = list(zipcode.geohash)
        distances: "collections.OrderedDict[int, float]" = collections.OrderedDict()
        while gh:
            sql = "SELECT id, latitude, longitude FROM sensors WHERE {}".format(
                " AND ".join([f"geohash_bit_{i}=?" for i in range(1, len(gh) + 1)])
            )
            if exclude:
                sql += " AND id NOT IN ({})".format(", ".join("?" for _ in exclude))
            cursor.execute(sql, tuple(gh) + tuple(exclude))
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
                    if len(distances) >= num_desired:
                        return distances
            gh.pop()
        return distances

    def _find_neighboring_sensors(
        self, zipcode: Sqlite3Zipcode
    ) -> "collections.OrderedDict[int, float]":  # See https://stackoverflow.com/a/52626233
        logger.info("Finding nearby sensors for %s", zipcode.zipcode)

        key = f"purpleair-distances-{zipcode.zipcode}"
        #
        # This is an OrderedDict from sensor ids to their distance from this zip.
        # We exclude them if they're "dead"; that is, not returning a valid reading.
        # If we do have dead sensors, we query the DB for other nearby sensors
        # so that we can (hopefully) find 10 active nearby sensors to read from.
        #
        neighboring_sensors = cache.get(key) or collections.OrderedDict()
        exclude = set(neighboring_sensors)
        for sensor_id in exclude:
            if self._is_dead(sensor_id):
                del neighboring_sensors[sensor_id]
        num_desired = self.MAX_SENSORS - len(neighboring_sensors)
        if num_desired:
            neighboring_sensors.update(
                self._refresh_sensor_distances(zipcode, exclude, num_desired)
            )
            cache.set(key, distances, timeout=60 * 60)

        return neighboring_sensors

    @staticmethod
    def _make_purpleair_pm25_key(sensor_id: int) -> str:
        return f"purpleair-pm25-sensor-{sensor_id}"

    @staticmethod
    def _mark_sensor_dead(sensor_id: int):
        cache.set(f"purpleair-pm25-sensor-dead-{sensor_id}", True, timeout=60 * 60)

    @staticmethod
    def _is_dead(sensor_id: int) -> bool:
        return bool(cache.get(f"purpleair-pm25-sensor-dead-{sensor_id}"))

    def _get_sensors_for_zipcode(self, zipcode: str) -> typing.List[Sensor]:
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM zipcodes WHERE zipcode=?", (zipcode,))
        row = cursor.fetchone()
        conn.close()
        if not row:
            return []

        # Now get the closest sensors, mapped to their distance
        sqlite3_zip = Sqlite3Zipcode.from_row(row)
        sensors_without_known_pm25 = self._find_neighboring_sensors(sqlite3_zip)
        if not sensors_without_known_pm25:
            return []

        # Get a list of sensors for which we already have good pm25 data.
        # We won't be needing to get these from the cache.
        sensors = []
        for sensor_id, distance in list(sensors_without_known_pm25.items()):
            pm25 = cache.get(self._make_purpleair_pm25_key(sensor_id))
            if pm25:
                sensors.append(Sensor(sensor_id, pm25, distance))
                del sensors_without_known_pm25[sensor_id]

        if sensors_without_known_pm25:
            logger.info(
                "Retrieving pm25 data from purpleair for %s sensors: %s",
                len(sensors_without_known_pm25),
                set(sensors_without_known_pm25),
            )
            try:
                resp = requests.get(
                    "https://www.purpleair.com/json?show={}".format(
                        "|".join(map(str, sensors_without_known_pm25))
                    )
                )
                resp.raise_for_status()
            except requests.RequestException as e:
                logger.exception(
                    "Error retrieving data for sensors %s and zipcode %s: %s",
                    set(sensors_without_known_pm25),
                    zipcode,
                    e,
                )
            else:
                for r in resp.json().get("results"):
                    if not r.get("ParentID"):
                        pm25 = float(r.get("PM2_5Value", 0))
                        if pm25 <= 0 or pm25 > 500:
                            logger.warning(
                                "Marking sensor %s dead because its pm25 is %s",
                                r["ID"],
                                pm25,
                            )
                            self._mark_sensor_dead(r["ID"])
                        else:
                            distance = sensors_without_known_pm25.get(r["ID"])
                            if distance is None:
                                logger.warning(
                                    "Mismatch: sensor %s has no corresponding distance",
                                    r["ID"],
                                )
                            else:
                                del sensors_without_known_pm25[r["ID"]]
                                cache.set(
                                    self._make_purpleair_pm25_key(r["ID"]),
                                    pm25,
                                    timeout=60 * 10,
                                )  # 10 minutes
                                sensors.append(Sensor(r["ID"], distance, pm25))

                # This should be empty now if we've gotten pm25 info
                # for every sensor.
                if sensors_without_known_pm25:
                    logger.warning("No results for ids: %s", set(sensors_without_known_pm25))

        return sorted(sensors, key=lambda s: s.distance)

    def get_metrics(self, zipcode: str) -> typing.Optional[Metrics]:
        self._check_database()

        sensors = self._get_sensors_for_zipcode(zipcode)
        if not sensors:
            return None

        average_pm25 = round(sum(s.pm25 for s in sensors) / len(sensors), ndigits=3)

        return Metrics(
            pm25=average_pm25,
            num_sensors=len(sensors),
            max_sensor_distance=round(sensors[-1].distance, ndigits=3),
            readings=[round(s.pm25, ndigits=3) for s in sensors],
        )


PURPLEAIR_PROVIDER = PurpleairProvider()
