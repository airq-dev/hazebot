import collections
import logging
import requests
import math
import sqlite3
import textwrap


logger = logging.getLogger(__name__)


Sensor = collections.namedtuple("Sensor", ["id", "pm_25"])


def haversine_distance(lon1, lat1, lon2, lat2):
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


def _get_connection():
    conn = sqlite3.connect("airq/providers/purpleair.db")
    conn.row_factory = sqlite3.Row
    return conn


def _find_neighboring_sensor_ids(zipcode, max_distance=15):
    conn = _get_connection()
    cursor = conn.cursor()
    gh = [zipcode[f"geohash_bit_{i + 1}"] for i in range(12)]
    while gh:
        sql = textwrap.dedent(
            """
            SELECT id, latitude, longitude
            FROM sensors
            WHERE {}
            """.format(
                " AND ".join([f"geohash_bit_{i}=?" for i in range(1, len(gh) + 1)])
            )
        )
        cursor.execute(sql, tuple(gh))
        rows = cursor.fetchall()
        if rows:
            conn.close()
            sensor_ids = [
                row['id']
                for row in rows
                if haversine_distance(
                    zipcode["longitude"],
                    zipcode["latitude"],
                    row["longitude"],
                    row["latitude"],
                )
                <= max_distance
            ]
            return sensor_ids
        gh.pop()


def _get_sensors_for_zipcode(zipcode):
    conn = _get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM zipcodes WHERE zipcode=?", (zipcode,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return

    # Now get the closest sensors
    sensor_ids = _find_neighboring_sensor_ids(row)
    if not sensor_ids:
        return

    try:
        resp = requests.get(
            "https://www.purpleair.com/json?show={}".format(
                "|".join(map(str, sensor_ids))
            )
        )
    except requests.RequestException as e:
        logger.exception(
            "Error retrieving data for sensor %s and zipcode %s: %s",
            sensor_id,
            zipcode["zipcode"],
            e,
        )
    else:
        return [
            Sensor(s["ID"], float(s["PM2_5Value"])) for s in resp.json().get("results")
            # Less than 0 or greater than 500 is, we hope, some kind of fluke.
            # I've seen it in the data...
            if 0 < float(s.get('PM2_5Value', 0)) < 500
        ]


def get_message_for_zipcode(zipcode):
    sensors = _get_sensors_for_zipcode(zipcode)
    if sensors:
        average_pm_25 = round(sum(s.pm_25 for s in sensors) / len(sensors), ndigits=3)
        return f"Average pm25 near {zipcode}: {average_pm_25} (sensors: {', '.join([str(s.id) for s in sensors])})"
