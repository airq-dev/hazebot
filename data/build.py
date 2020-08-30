import decimal
import geohash
import json
import math
import os
import requests
import sqlite3
import shutil
import textwrap
import zipfile


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


def refresh_data():
    try:
        os.remove("airq.db")
    except FileNotFoundError:
        pass

    try:
        os.remove("US.zip")
    except FileNotFoundError:
        pass

    try:
        os.remove("purpleair.json")
    except FileNotFoundError:
        pass


def get_connection():
    return sqlite3.connect("airq.db")


def create_db():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        textwrap.dedent(
            """
        CREATE TABLE sensors (
            id INTEGER PRIMARY KEY,
            zipcode INTEGER,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL,
            geohash_bit_1 VARCHAR NOT NULL,
            geohash_bit_2 VARCHAR NOT NULL,
            geohash_bit_3 VARCHAR NOT NULL,
            geohash_bit_4 VARCHAR NOT NULL,
            geohash_bit_5 VARCHAR NOT NULL,
            geohash_bit_6 VARCHAR NOT NULL,
            geohash_bit_7 VARCHAR NOT NULL,
            geohash_bit_8 VARCHAR NOT NULL,
            geohash_bit_9 VARCHAR NOT NULL,
            geohash_bit_10 VARCHAR NOT NULL,
            geohash_bit_11 VARCHAR NOT NULL,
            geohash_bit_12 VARCHAR NOT NULL,
            FOREIGN KEY(zipcode) REFERENCES zipcodes(id)
        );
    """
        )
    )
    cursor.execute(
        textwrap.dedent(
            """
        CREATE TABLE zipcodes (
            id INTEGER PRIMARY KEY,
            zipcode VARCHAR UNIQUE,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL,
            geohash_bit_1 VARCHAR NOT NULL,
            geohash_bit_2 VARCHAR NOT NULL,
            geohash_bit_3 VARCHAR NOT NULL,
            geohash_bit_4 VARCHAR NOT NULL,
            geohash_bit_5 VARCHAR NOT NULL,
            geohash_bit_6 VARCHAR NOT NULL,
            geohash_bit_7 VARCHAR NOT NULL,
            geohash_bit_8 VARCHAR NOT NULL,
            geohash_bit_9 VARCHAR NOT NULL,
            geohash_bit_10 VARCHAR NOT NULL,
            geohash_bit_11 VARCHAR NOT NULL,
            geohash_bit_12 VARCHAR NOT NULL
        );
    """
        )
    )
    conn.commit()


def get_zipcodes_from_geonames():
    r = requests.get("http://download.geonames.org/export/zip/US.zip", stream=True)
    with open("US.zip", "wb") as fd:
        for chunk in r.iter_content(chunk_size=512):
            fd.write(chunk)

    with zipfile.ZipFile("US.zip") as zf:
        with zf.open("US.txt", "r") as fd:
            for line in fd.readlines():
                fields = line.decode().strip().split("\t")
                zipcode = fields[1].strip()
                latitude = decimal.Decimal(fields[9].strip())
                longitude = decimal.Decimal(fields[10].strip())
                place_name = fields[2].strip()
                # Skip army prefixes
                if not place_name.startswith(("FPO", "APO")):
                    yield zipcode, latitude, longitude


def create_zipcodes():
    print("Creating zipcodes")
    for i, (zipcode, latitude, longitude) in enumerate(get_zipcodes_from_geonames()):
        if i % 50 == 0:
            print(f"Created {i} zipcodes")
        gh = geohash.encode(latitude, longitude)
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            textwrap.dedent(
                """
            INSERT INTO zipcodes 
            VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
            ),
            (
                i,
                zipcode,
                round(float(latitude), ndigits=6),
                round(float(longitude), ndigits=6),
                *list(gh),
            ),
        )
        conn.commit()


def find_zipcode(lat, lon, gh):
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    while gh:
        sql = textwrap.dedent(
            """
            SELECT id, latitude, longitude
            FROM zipcodes
            WHERE {}
            """.format(
                " AND ".join([f"geohash_bit_{i + 1}=?" for i, _ in enumerate(gh)])
            )
        )
        cursor.execute(sql, tuple(gh))
        rows = cursor.fetchall()
        if rows:
            conn.close()
            closest_zip = None
            smallest_distance = float("inf")
            for row in rows:
                distance = haversine_distance(
                    lon, lat, row["longitude"], row["latitude"]
                )
                if distance <= 25 and smallest_distance > distance:
                    closest_zip = row["id"]
                    smallest_distance = distance
            return closest_zip
        gh = gh[:-1]


def get_purpleair_data():
    if not os.path.exists("purpleair.json"):
        resp = requests.get("https://www.purpleair.com/json")
        resp.raise_for_status()
        with open("purpleair.json", "w") as fd:
            json.dump(resp.json()["results"], fd)
    with open("purpleair.json", "r") as fd:
        return json.load(fd)


def create_sensors():
    print("Creating sensors")
    results = get_purpleair_data()
    num_created = 0
    for result in results:
        if result.get("DEVICE_LOCATIONTYPE") != "outside":
            continue
        if result.get("ParentID"):
            # I don't know what this means but feel it's probably
            # best to skip?
            continue
        latitude = result.get("Lat")
        longitude = result.get("Lon")
        if not latitude or not longitude:
            continue
        gh = geohash.encode(latitude, longitude)
        zipcode_id = find_zipcode(latitude, longitude, gh)
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            textwrap.dedent(
                """
            INSERT INTO sensors
            VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
            ),
            (
                result["ID"],
                zipcode_id,
                round(float(latitude), ndigits=6),
                round(float(longitude), ndigits=6),
                *list(gh),
            ),
        )
        conn.commit()
        num_created += 1
        if num_created % 50 == 0:
            print(f"Created {num_created} sensors of {len(results)} purpleair sensors")


def generate():
    refresh_data()
    create_db()
    create_zipcodes()
    create_sensors()
    shutil.copyfile("airq.db", "../app/airq/providers/purpleair.db")


if __name__ == "__main__":
    generate()
