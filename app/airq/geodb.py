import collections
import dataclasses
import sqlite3
import typing

from airq import cache
from airq import util


DB_PATH = "airq/purpleair.db"


class Sensor(typing.NamedTuple):
    sensor_id: int
    distance: float


class Zipcode(typing.NamedTuple):
    zipcode: str
    city_id: int
    distance: float


CITY_NAMES: cache.Cache[int, str] = cache.Cache(
    prefix="city-names-", timeout=24 * 60 * 60, use_remote=False
)


SENSORS: cache.Cache[int, typing.List[Sensor]] = cache.Cache(
    prefix="sensors-", timeout=24 * 60 * 60, use_remote=False
)


def _get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def get_city_names(city_ids: typing.Set[int]) -> typing.Dict[int, str]:
    if not city_ids:
        return {}
    city_names = CITY_NAMES.get_many(city_ids)
    city_ids -= city_names.keys()
    if city_ids:
        conn = _get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, name FROM cities WHERE id IN ({})".format(
                ", ".join(["?" for _ in city_ids])
            ),
            tuple(city_ids),
        )
        db_city_names = {row["id"]: row["name"] for row in cursor.fetchall()}
        CITY_NAMES.set_many(db_city_names)
        city_names.update(db_city_names)
    return city_names


@cache.memoize(timeout=24 * 60 * 60, use_remote=False)
def get_zipcode_raw(zipcode: str) -> typing.Optional[typing.Dict[str, typing.Any]]:
    if not zipcode.isdigit() or len(zipcode) != 5:
        return None
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM zipcodes WHERE zipcode=?", (zipcode,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    return dict(row)


@cache.memoize(timeout=24 * 60 * 60, use_remote=False)
def get_nearby_zipcodes(
    zipcode: str, *, max_radius: int, num_desired: int
) -> typing.Dict[int, Zipcode]:
    zipcodes: typing.Dict[int, Zipcode] = {}
    row = get_zipcode_raw(zipcode)
    if not row:
        return zipcodes

    zipcodes[row["id"]] = Zipcode(row["zipcode"], row["city_id"], 0)
    latitude = row["latitude"]
    longitude = row["longitude"]
    gh = [row[f"geohash_bit_{i + 1}"] for i in range(12)]

    conn = _get_connection()
    cursor = conn.cursor()

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
    zipcodes_to_sensors = SENSORS.get_many(zipcode_ids)
    zipcode_ids -= zipcodes_to_sensors.keys()
    if zipcode_ids:
        conn = _get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT sensor_id, zipcode_id, distance FROM sensors_zipcodes WHERE zipcode_id IN ({})".format(
                ", ".join(["?" for _ in zipcode_ids])
            ),
            tuple(zipcode_ids),
        )
        db_zipcodes_to_sensors: typing.Dict[
            int, typing.List[Sensor]
        ] = collections.defaultdict(list)
        for row in cursor.fetchall():
            db_zipcodes_to_sensors[row["zipcode_id"]].append(
                Sensor(row["sensor_id"], row["distance"])
            )
        SENSORS.set_many(db_zipcodes_to_sensors)
        zipcodes_to_sensors.update(db_zipcodes_to_sensors)
    return dict(zipcodes_to_sensors)
