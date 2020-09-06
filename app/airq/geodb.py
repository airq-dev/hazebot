import collections
import dataclasses
import sqlite3
import typing

from airq import util


DB_PATH = "airq/purpleair.db"


class City(typing.NamedTuple):
    name: str
    state_code: str


class Sensor(typing.NamedTuple):
    sensor_id: int
    distance: float


class Zipcode(typing.NamedTuple):
    zipcode: str
    city_id: int
    distance: float


def _get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def get_cities(city_ids: typing.Set[int]) -> typing.Dict[int, City]:
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, state_code FROM cities WHERE id IN ({})".format(", ".join(["?" for _ in city_ids])), tuple(city_ids))
    return {
        row['id']: City(row['name'], row['state_code'])
        for row in cursor.fetchall()
    }



def get_nearby_zipcodes(
    zipcode: str, *, max_radius: int, num_desired: int
) -> typing.Dict[int, Zipcode]:
    conn = _get_connection()
    cursor = conn.cursor()

    zipcodes: typing.Dict[int, Zipcode] = {}

    cursor.execute("SELECT * FROM zipcodes WHERE zipcode=?", (zipcode,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return zipcodes

    zipcodes[row["id"]] = Zipcode(row['zipcode'], row['city_id'], 0)
    latitude = row["latitude"]
    longitude = row["longitude"]
    gh = [row[f"geohash_bit_{i + 1}"] for i in range(12)]

    while gh:
        sql = "SELECT id, zipcode, city_id, latitude, longitude FROM zipcodes WHERE {} AND id NOT IN ({})".format(
            " AND ".join([f"geohash_bit_{i}=?" for i in range(1, len(gh) + 1)]),
            ", ".join("?" for _ in zipcodes),
        )
        cursor.execute(sql, tuple(gh) + tuple(zipcodes))
        for zipcode_id, zipcode, city_id, distance in sorted(
            [
                (
                    r["id"],
                    r["zipcode"],
                    r["city_id"],
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
                zipcodes[zipcode_id] = Zipcode(zipcode, city_id, distance)
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
