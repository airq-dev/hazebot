import collections
import logging
import sqlite3
import typing

from airq import util


DB_PATH = "airq/purpleair.db"


logger = logging.getLogger(__name__)


def _get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def get_sensor_distances(
    zipcode: str, exclude: typing.Set[int], num_desired: int, max_radius: int
) -> "collections.OrderedDict[int, float]":  # See https://stackoverflow.com/a/52626233
    logger.info(
        "get_nearby_sensors for %s for %s sensors", zipcode, num_desired,
    )

    distances: "collections.OrderedDict[int, float]" = collections.OrderedDict()
    sensors: typing.List[typing.Tuple[int, float]] = []

    conn = _get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM zipcodes WHERE zipcode=?", (zipcode,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return distances

    latitude = row["latitude"]
    longitude = row["longitude"]
    gh = [row[f"geohash_bit_{i + 1}"] for i in range(12)]

    while gh or sensors:
        if sensors:
            sensor_id, distance = sensors.pop()
            if distance > max_radius:
                break
            distances[sensor_id] = distance
            if len(distances) >= num_desired:
                break
        else:
            sql = "SELECT id, latitude, longitude FROM sensors WHERE {}".format(
                " AND ".join([f"geohash_bit_{i}=?" for i in range(1, len(gh) + 1)])
            )
            if exclude:
                sql += " AND id NOT IN ({})".format(", ".join("?" for _ in exclude))
            cursor.execute(sql, tuple(gh) + tuple(exclude))
            # We will sort the sensors by distance and add them until we have MAX_SENSORS
            # sensors. As soon as we see a sensor further away than MAX_RADIUS, we're done.
            sensors = sorted(
                [
                    (
                        r["id"],
                        util.haversine_distance(
                            row["longitude"],
                            row["latitude"],
                            r["longitude"],
                            r["latitude"],
                        ),
                    )
                    for r in cursor.fetchall()
                    if r["id"] not in distances
                ],
                key=lambda t: t[1],
            )
            gh.pop()

    conn.close()
    return distances
