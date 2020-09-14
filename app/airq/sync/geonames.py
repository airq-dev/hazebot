import collections
import decimal
import geohash
import gzip
import logging
import requests
import typing
import zipfile

from airq.config import db
from airq.lib.util import chunk_list
from airq.models.cities import City
from airq.models.zipcodes import Zipcode


logger = logging.getLogger(__name__)


TGeonamesData = typing.List[
    typing.Tuple[str, str, str, decimal.Decimal, decimal.Decimal]
]
TCitiesMap = typing.Dict[str, typing.Dict[str, City]]


COUNTRY_CODE = "US"
GEONAMES_URL = f"http://download.geonames.org/export/zip/{COUNTRY_CODE}.zip"
ZIP_2_TIMEZONES_URL = "https://sourceforge.net/projects/zip2timezone/files/timezonebyzipcode_20120424.sql.gz/download"
ARMY_PREFIXES = ("FPO", "APO")


def _download_zipfile(url: str, filename: str):
    resp = requests.get(url, stream=True)
    resp.raise_for_status()
    with open(filename, "wb") as fd:
        for chunk in resp.iter_content(chunk_size=512):
            fd.write(chunk)


def _get_geonames_data() -> TGeonamesData:
    zipfile_name = f"{COUNTRY_CODE}.zip"
    _download_zipfile(GEONAMES_URL, zipfile_name)

    geonames_data = []
    with zipfile.ZipFile(zipfile_name) as zf:
        with zf.open(f"{COUNTRY_CODE}.txt", "r") as fd:  # type: ignore
            for line in fd.readlines():
                fields = line.decode().strip().split("\t")
                zipcode = fields[1].strip()
                city_name = fields[2].strip()
                state_code = fields[4].strip()
                latitude = decimal.Decimal(fields[9].strip())
                longitude = decimal.Decimal(fields[10].strip())
                place_name = fields[2].strip()
                if place_name.startswith(ARMY_PREFIXES):
                    continue
                geonames_data.append(
                    (zipcode, city_name, state_code, latitude, longitude)
                )

    return geonames_data


def _get_timezones_data() -> typing.Dict[str, str]:
    filename = "zipcodes_to_timezones.gz"
    _download_zipfile(ZIP_2_TIMEZONES_URL, filename)

    zipcode_to_timezones = {}
    with gzip.open(filename) as f:
        for line in f:
            line = line.decode().strip()
            if line.startswith("INSERT INTO"):
                i = 0
                while line[i] != "(":
                    i += 1
                i += 1  # Skip the leading "("
                j = len(line) - 1
                j -= 1  # Skip the trailing ";"
                j -= 1  # Skip the trailing ")"
                row_defs = line[i:j].split("),(")
                for row_def in row_defs:
                    fields = row_def.split(",")
                    zipcode = fields[1][1:-1].strip()
                    timezone = fields[6][1:-1].strip()
                    zipcode_to_timezones[zipcode] = timezone

    return zipcode_to_timezones


def _build_cities_map(geonames_data: TGeonamesData) -> TCitiesMap:
    cities_map: TCitiesMap = collections.defaultdict(dict)
    for city in City.query.all():
        cities_map[city.state_code][city.name] = city
    new_cities = []
    for _, city_name, state_code, _, _ in geonames_data:
        city = cities_map.get(state_code, {}).get(city_name)
        if city is None:
            city = City(name=city_name, state_code=state_code)
            cities_map[state_code][city_name] = city
            new_cities.append(city)

    if new_cities:
        logger.info("Creating %s cities", len(new_cities))
        db.session.bulk_save_objects(new_cities)
        db.session.commit()
        for city in City.query.all():
            cities_map[city.state_code][city.name] = city

    return cities_map


def _zipcodes_sync(
    geonames_data: TGeonamesData,
    cities_map: TCitiesMap,
    timezones_map: typing.Dict[str, str],
):
    existing_zipcodes = {zipcode.zipcode: zipcode for zipcode in Zipcode.query.all()}
    updates = []
    new_zipcodes = []
    for zipcode, city_name, state_code, latitude, longitude in geonames_data:
        obj = existing_zipcodes.get(zipcode)
        timezone = timezones_map.get(zipcode)
        if (
            not obj
            or obj.latitude != latitude
            or obj.longitude != longitude
            or timezone != obj.timezone
        ):
            gh = geohash.encode(latitude, longitude)
            data = dict(
                zipcode=zipcode,
                city_id=cities_map[state_code][city_name].id,
                latitude=latitude,
                longitude=longitude,
                timezone=timezone,
                **{f"geohash_bit_{i}": c for i, c in enumerate(gh, start=1)},
            )
            if obj:
                data["id"] = obj.id
                updates.append(data)
            else:
                new_zipcodes.append(Zipcode(**data))

    if new_zipcodes:
        logger.info("Creating %s zipcodes", len(new_zipcodes))
        for objects in chunk_list(new_zipcodes):
            db.session.bulk_save_objects(objects)
            db.session.commit()

    if updates:
        logger.info("Updating %s zipcodes", len(updates))
        for mappings in chunk_list(updates):
            db.session.bulk_update_mappings(Zipcode, mappings)
            db.session.commit()


def geonames_sync():
    logger.info("Retrieving timezone data from sourceforge")
    timezones_map = _get_timezones_data()

    logger.info("Retrieving zipcode data from geonames")
    geonames_data = _get_geonames_data()

    logger.info("Syncing cities from %s entries", len(geonames_data))
    cities_map = _build_cities_map(geonames_data)

    logger.info("Syncing zipcodes from %s entries", len(geonames_data))
    _zipcodes_sync(geonames_data, cities_map, timezones_map)
