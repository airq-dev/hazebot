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
    zipcode: str, *, exclude_ids: typing.Set[int], num_desired: int, max_radius: int
) -> typing.Dict[int, float]:
    logger.info(
        "get_nearby_sensors for %s for %s sensors", zipcode, num_desired,
    )

    sensor_to_distance: typing.Dict[int, float] = {}

    conn = _get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM zipcodes WHERE zipcode=?", (zipcode,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return sensor_to_distance

    latitude = row["latitude"]
    longitude = row["longitude"]
    gh = [row[f"geohash_bit_{i + 1}"] for i in range(12)]

    unprocessed_sensors: typing.List[typing.Tuple[int, float]] = []
    while gh or unprocessed_sensors:
        if unprocessed_sensors:
            sensor_id, distance = unprocessed_sensors.pop()
            if distance > max_radius:
                break
            sensor_to_distance[sensor_id] = distance
            if len(sensor_to_distance) >= num_desired:
                break
        else:
            sql = "SELECT id, latitude, longitude FROM sensors WHERE {}".format(
                " AND ".join([f"geohash_bit_{i}=?" for i in range(1, len(gh) + 1)])
            )
            if exclude_ids:
                sql += " AND id NOT IN ({})".format(", ".join("?" for _ in exclude_ids))
            cursor.execute(sql, tuple(gh) + tuple(exclude_ids))
            # We will sort the sensors by distance and add them until we have MAX_SENSORS
            # sensors. As soon as we see a sensor further away than MAX_RADIUS, we're done.
            unprocessed_sensors = sorted(
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
                    if r["id"] not in sensor_to_distance
                ],
                key=lambda t: t[1],
            )
            gh.pop()

    conn.close()
    return sensor_to_distance
