import json
import os
import pathlib
import requests
import shutil
import zipfile

from airq.lib.geo import haversine_distance
from airq.lib.http import chunked_download
from airq.lib.purpleair import call_purpleair_sensors_api
from airq.sync.geonames import COUNTRY_CODE
from airq.sync.geonames import GEONAMES_URL
from tests.base import BaseTestCase


COORDINATES = (45.5181, -122.6745)  # Central Portland
RADIUS = 100


def _is_in_range(lat: float, lon: float):
    return haversine_distance(lon, lat, COORDINATES[1], COORDINATES[0]) < RADIUS


def generate_fixtures():
    """
    Generates fixture data for all zipcodes and sensors within 100km of central Portland.

    We test on this subset of real data to keep test speed down.

    I would caution against running this script unless absolutely necessary because doing so
    will force you to fix a bunch of tests.

    """
    path = pathlib.Path(__file__).parent.parent.parent / "tests" / "fixtures"
    timestamp = BaseTestCase().get_mock_datetime().timestamp()

    resp = call_purpleair_sensors_api()
    response_json = resp.json()
    results = []
    num_skipped = 0

    fields = response_json["fields"]
    latitude_idx = fields.index("latitude")
    longitude_idx = fields.index("longitude")
    last_seen_idx = fields.index("last_seen")

    for data in response_json["data"]:
        latitude = data[latitude_idx]
        longitude = data[longitude_idx]
        if (
            latitude is not None
            and longitude is not None
            and _is_in_range(latitude, longitude)
        ):
            data[last_seen_idx] = timestamp
            results.append(data)
        else:
            num_skipped += 1
    response_json["data"] = results
    file_path = path / "purpleair/purpleair.json"
    with file_path.open("w") as f:
        json.dump(response_json, f)
    print(f"Skipped {num_skipped} sensors (wrote {len(results)})")

    tmpfile = "/tmp/geonames.zip"
    try:
        os.remove(tmpfile)
    except FileNotFoundError:
        pass
    chunked_download(GEONAMES_URL, tmpfile)
    lines = ""
    num_kept = 0
    num_skipped = 0
    with zipfile.ZipFile(tmpfile) as zf:
        with zf.open(f"{COUNTRY_CODE}.txt", "r") as fd:
            for line in fd.readlines():
                fields = line.decode().strip().split("\t")
                latitude = float(fields[9].strip())
                longitude = float(fields[10].strip())
                if _is_in_range(latitude, longitude):
                    num_kept += 1
                    lines += line.decode()
                else:
                    num_skipped += 1

    tmpdir = "/tmp/geonames_out.zip"
    try:
        shutil.rmtree(tmpdir)
    except FileNotFoundError:
        pass
    os.mkdir(tmpdir)
    file_name = f"{tmpdir}/{COUNTRY_CODE}.txt"
    with open(file_name, "w") as f:
        f.write(lines)
    file_path = path / f"geonames/{COUNTRY_CODE}.zip"
    with zipfile.ZipFile(file_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(file_name, os.path.basename(file_name))
    print(f"Skipped {num_skipped} zipcodes (wrote {num_kept})")
