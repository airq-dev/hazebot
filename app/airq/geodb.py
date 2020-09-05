import collections
import logging
import sqlite3
import typing

from airq import cache
from airq import util


DB_PATH = "airq/purpleair.db"


logger = logging.getLogger(__name__)


def _get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@cache.CACHE.memoize(timeout=24 * 60 * 60)
def get_nearby_zipcodes(
    zipcode: str, radius: int
) -> typing.Dict[int, typing.Tuple[str, float]]:
    logger.info("Retrieving zipcodes within %s of %s", radius, zipcode)

    conn = _get_connection()
    cursor = conn.cursor()

    zipcodes: typing.Dict[int, typing.Tuple[str, float]] = {}

    cursor.execute("SELECT * FROM zipcodes WHERE zipcode=?", (zipcode,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return zipcodes

    zipcodes[row["id"]] = (zipcode, 0)
    latitude = row["latitude"]
    longitude = row["longitude"]
    gh = [row[f"geohash_bit_{i + 1}"] for i in range(12)]

    while gh:
        sql = "SELECT id, zipcode, latitude, longitude FROM zipcodes WHERE {} AND id NOT IN ({})".format(
            " AND ".join([f"geohash_bit_{i}=?" for i in range(1, len(gh) + 1)]),
            ", ".join("?" for _ in zipcodes),
        )
        cursor.execute(sql, tuple(gh) + tuple(zipcodes))
        for zipcode_id, zipcode, distance in sorted(
            [
                (
                    r["id"],
                    r["zipcode"],
                    util.haversine_distance(
                        row["longitude"],
                        row["latitude"],
                        r["longitude"],
                        r["latitude"],
                    ),
                )
                for r in cursor.fetchall()
            ],
            key=lambda t: t[1],
        ):
            if distance > radius:
                conn.close()
                return zipcodes
            zipcodes[zipcode_id] = (zipcode, distance)
        gh.pop()

    conn.close()
    return zipcodes


def get_sensors_for_zipcodes(
    zipcode_ids: typing.Set[int],
) -> typing.Dict[int, typing.List[typing.Tuple[int, float]]]:
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT sensor_id, zipcode_id, distance FROM sensors_zipcodes WHERE zipcode_id IN ({})".format(
            ", ".join(["?" for _ in zipcode_ids])
        ),
        tuple(zipcode_ids),
    )
    zipcodes_to_sensors = collections.defaultdict(list)
    for row in cursor.fetchall():
        zipcodes_to_sensors[row["zipcode_id"]].append(
            (row["sensor_id"], row["distance"])
        )
    return dict(zipcodes_to_sensors)
