import logging
import requests
import math
import sqlite3
import textwrap


logger = logging.getLogger(__name__)


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


def _find_nearest_sensor(zipcode):
    conn = _get_connection()
    cursor = conn.cursor()
    sql = "SELECT id, latitude, longitude FROM sensors WHERE zipcode=?"
    cursor.execute(sql, (zipcode["id"],))
    rows = cursor.fetchall()
    conn.close()
    if rows:
        closest_sensor = None
        smallest_distance = float("inf")
        for row in rows:
            distance = haversine_distance(
                zipcode["longitude"],
                zipcode["latitude"],
                row["longitude"],
                row["latitude"],
            )
            if distance <= 25 and smallest_distance > distance:
                closest_sensor = row["id"]
                smallest_distance = distance
        return closest_sensor


def _get_sensor_for_zipcode(zipcode):
    conn = _get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM zipcodes WHERE zipcode=?", (zipcode,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return

    # Now get the closest sensor
    sensor_id = _find_nearest_sensor(row)
    if not sensor_id:
        return

    try:
        resp = requests.get("https://www.purpleair.com/json?show={}".format(sensor_id))
    except requests.RequestException as e:
        logger.exception(
            "Error retrieving data for sensor %s and zipcode %s: %s",
            sensor_id,
            zipcode["zipcode"],
            e,
        )
    else:
        results = resp.json().get("results")
        if results:
            return results[0]


def get_message_for_zipcode(zipcode):
    sensor = _get_sensor_for_zipcode(zipcode)
    if sensor:
        return f"pm25 near {zipcode}: {sensor['PM2_5Value']} (sensor_id: {sensor['ID']})"
