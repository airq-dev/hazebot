import collections
import decimal
import geohash
import logging
import requests
import typing
import zipfile

from airq.config import db
from airq.models.cities import City
from airq.models.zipcodes import Zipcode


logger = logging.getLogger(__name__)


TGeonamesData = typing.List[
    typing.Tuple[str, str, str, decimal.Decimal, decimal.Decimal]
]
TCitiesMap = typing.Dict[str, typing.Dict[str, City]]


COUNTRY_CODE = "US"
GEONAMES_URL = f"http://download.geonames.org/export/zip/{COUNTRY_CODE}.zip"
ARMY_PREFIXES = ("FPO", "APO")


def _get_geonames_data() -> TGeonamesData:
    resp = requests.get(GEONAMES_URL, stream=True)
    resp.raise_for_status()
    zipfile_name = f"{COUNTRY_CODE}.zip"
    with open(zipfile_name, "wb") as fd:
        for chunk in resp.iter_content(chunk_size=512):
            fd.write(chunk)

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


def _zipcodes_sync(geonames_data: TGeonamesData, cities_map: TCitiesMap):
    existing_zipcodes = {zipcode.zipcode: zipcode for zipcode in Zipcode.query.all()}
    updates = []
    new_zipcodes = []
    for zipcode, city_name, state_code, latitude, longitude in geonames_data:
        obj = existing_zipcodes.get(zipcode)
        if not obj or obj.latitude != latitude or obj.longitude != longitude:
            gh = geohash.encode(latitude, longitude)
            data = dict(
                zipcode=zipcode,
                city_id=cities_map[state_code][city_name].id,
                latitude=latitude,
                longitude=longitude,
                **{f"geohash_bit_{i}": c for i, c in enumerate(gh, start=1)},
            )
            if obj:
                data["id"] = obj.id
                updates.append(data)
            else:
                new_zipcodes.append(Zipcode(**data))

    if new_zipcodes:
        logger.info("Creating %s zipcodes", len(new_zipcodes))
        db.session.bulk_save_objects(new_zipcodes)
        db.session.commit()

    if updates:
        logger.info("Updating %s zipcodes", len(updates))
        db.session.bulk_update_mappings(Zipcode, updates)
        db.session.commit()


def geonames_sync():
    logger.info("Retrieving zipcode data from geonames")
    geonames_data = _get_geonames_data()

    logger.info("Syncing cities from %s entries", len(geonames_data))
    cities_map = _build_cities_map(geonames_data)

    logger.info("Syncing zipcodes from %s entries", len(geonames_data))
    _zipcodes_sync(geonames_data, cities_map)
