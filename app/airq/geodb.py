import collections
import dataclasses
import sqlite3
import typing

from airq import cache
from airq import util


DB_PATH = "airq/purpleair.db"


class Zipcode(typing.NamedTuple):
    zipcode: str
    distance: float


class Sensor(typing.NamedTuple):
    sensor_id: int
    distance: float


def _get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def get_zipcode_raw(zipcode: str) -> typing.Dict[str, typing.Any]:
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM zipcodes WHERE zipcode=?", (zipcode,))
    row = cursor.fetchone()
    conn.close()
    return row


def get_nearby_zipcodes(
    zipcode: str, *, max_radius: int, num_desired: int
) -> typing.Dict[int, Zipcode]:
    zipcodes: typing.Dict[int, Zipcode] = {}
    row = get_zipcode_raw(zipcode)
    if not row:
        return zipcodes

    conn = _get_connection()
    cursor = conn.cursor()

    zipcodes[row["id"]] = Zipcode(zipcode, 0)
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
            if distance <= max_radius:
                zipcodes[zipcode_id] = Zipcode(zipcode, distance)
            if len(zipcodes) >= num_desired:
                conn.close()
                return zipcodes
        gh.pop()

    conn.close()
    return zipcodes


def get_sensors_for_zipcodes(
    zipcode_ids: typing.Set[int],
) -> typing.Dict[int, typing.List[Sensor]]:
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT sensor_id, zipcode_id, distance FROM sensors_zipcodes WHERE zipcode_id IN ({})".format(
            ", ".join(["?" for _ in zipcode_ids])
        ),
        tuple(zipcode_ids),
    )
    zipcodes_to_sensors: typing.Mapping[
        int, typing.List[Sensor]
    ] = collections.defaultdict(list)
    for row in cursor.fetchall():
        zipcodes_to_sensors[row["zipcode_id"]].append(
            Sensor(row["sensor_id"], row["distance"])
        )
    return dict(zipcodes_to_sensors)
