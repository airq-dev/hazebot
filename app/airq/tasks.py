import collections
import datetime
import decimal
import geohash
import requests
import time
import typing
import zipfile

from airq.celery import celery
from airq.celery import get_celery_logger


def geonames_sync():
    from airq.models.cities import City
    from airq.models.zipcodes import Zipcode
    from airq.settings import db

    logger = get_celery_logger()
    logger.info("Retrieving zipcode data from geonames")

    resp = requests.get(
        "http://download.geonames.org/export/zip/allCountries.zip", stream=True
    )
    resp.raise_for_status()
    with open("allCountries.zip", "wb") as fd:
        for chunk in resp.iter_content(chunk_size=512):
            fd.write(chunk)

    geonames_data = []
    with zipfile.ZipFile("allCountries.zip") as zf:
        with zf.open("allCountries.txt", "r") as fd:
            for line in fd.readlines():
                fields = line.decode().strip().split("\t")
                country_code = fields[0].strip()
                if country_code != "US":
                    continue

                zipcode = fields[1].strip()
                city_name = fields[2].strip()
                state_code = fields[4].strip()

                latitude = decimal.Decimal(fields[9].strip())
                longitude = decimal.Decimal(fields[10].strip())
                place_name = fields[2].strip()
                # Skip army prefixes
                if place_name.startswith(("FPO", "APO")):
                    continue
                geonames_data.append(
                    (zipcode, city_name, state_code, latitude, longitude)
                )

    logger.info("Syncing cities from %s entries", len(geonames_data))

    cities_map = collections.defaultdict(dict)
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

    logger.info("Syncing zipcodes from %s entries", len(geonames_data))
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


def purpleair_sync():
    from airq import util
    from airq.models import sensors
    from airq.models.relations import SensorZipcodeRelation
    from airq.models.sensors import Sensor
    from airq.models.zipcodes import Zipcode
    from airq.settings import db

    logger = get_celery_logger()
    logger.info("Fetching sensor from purpleair")

    try:
        resp = requests.get("https://www.purpleair.com/json")
        resp.raise_for_status()
    except requests.RequestException:
        logger.exception("Error updating purpleair data")
        results = []
    else:
        results = resp.json().get("results", [])

    logger.info("Recieved %s sensors", len(results))

    existing_sensor_map = {s.id: s for s in Sensor.query.all()}

    relations_map = collections.defaultdict(dict)
    for relation in SensorZipcodeRelation.query.all():
        relations_map[relation.sensor_id][relation.zipcode_id] = relation.distance

    updates = []
    new_sensors = []
    moved_sensor_ids = []
    for result in results:
        if sensors.is_valid_reading(result):
            sensor = existing_sensor_map.get(result["ID"])
            latitude = result["Lat"]
            longitude = result["Lon"]
            pm25 = float(result["PM2_5Value"])
            data: typing.Dict[str, typing.Any] = {
                "id": result["ID"],
                "latest_reading": pm25,
                "updated_at": result["LastSeen"],
            }

            if (
                not sensor
                or sensor.latitude != latitude
                or sensor.longitude != longitude
            ):
                gh = geohash.encode(latitude, longitude)
                data.update(
                    latitude=latitude,
                    longitude=longitude,
                    **{f"geohash_bit_{i}": c for i, c in enumerate(gh, start=1)},
                )
                moved_sensor_ids.append(result["ID"])
            elif not relations_map.get(result["ID"]):
                moved_sensor_ids.append(result["ID"])

            if sensor:
                updates.append(data)
            else:
                new_sensors.append(Sensor(**data))

    if new_sensors:
        logger.info("Creating %s sensors", len(new_sensors))
        db.session.bulk_save_objects(new_sensors)
        db.session.commit()

    if updates:
        logger.info("Updating %s sensors", len(updates))
        db.session.bulk_update_mappings(Sensor, updates)
        db.session.commit()

    if not moved_sensor_ids:
        return

    logger.info("Syncing relations for %s sensors", len(moved_sensor_ids))

    trie = {}
    for zipcode in Zipcode.query.all():
        curr = trie
        for c in zipcode.geohash:
            if c not in curr:
                curr[c] = {}
            curr = curr[c]
        curr[zipcode.id] = zipcode

    new_relations = []
    updates = []

    sensors = Sensor.query.filter(Sensor.id.in_(moved_sensor_ids)).all()
    for sensor in sensors:
        gh = list(sensor.geohash)
        latitude = sensor.latitude
        longitude = sensor.longitude
        done = False
        zipcode_ids = set()
        while gh and not done:
            curr = trie
            for c in gh:
                curr = curr.get(c, {})
            zipcodes = []
            stack = [curr]
            while stack:
                curr = stack.pop()
                for v in curr.values():
                    if isinstance(v, Zipcode):
                        if v.id not in zipcode_ids:
                            zipcodes.append(v)
                    else:
                        stack.append(v)

            for zipcode_id, distance in sorted(
                [
                    (
                        z.id,
                        util.haversine_distance(
                            longitude, latitude, z.longitude, z.latitude
                        ),
                    )
                    for z in zipcodes
                ],
                key=lambda t: t[1],
            ):
                if distance >= 25:
                    done = True
                    break
                if len(zipcode_ids) >= 25:
                    done = True
                    break
                zipcode_ids.add(zipcode_id)
                current_distance = relations_map.get(sensor.id, {}).get(zipcode_id)
                if current_distance != distance:
                    data = {
                        "zipcode_id": zipcode_id,
                        "sensor_id": sensor.id,
                        "distance": distance,
                    }
                    if current_distance is None:
                        new_relations.append(SensorZipcodeRelation(**data))
                    else:
                        updates.append(data)
            gh.pop()

    if new_relations:
        logger.info("Creating %s relations", len(new_relations))
        for chunk in util.chunk_list(new_relations):
            db.session.bulk_save_objects(chunk)
            db.session.commit()

    if updates:
        logger.info("Updating %s relations", len(updates))
        for chunk in util.chunk_list(new_relations):
            db.session.bulk_update_mappings(SensorZipcodeRelation, chunk)
            db.session.commit()


def _should_sync_geonames() -> bool:
    from airq.models.zipcodes import Zipcode

    logger = get_celery_logger()

    now = datetime.datetime.now()
    hour = datetime.datetime(year=now.year, month=now.month, day=now.day, hour=now.hour)
    if (now.timestamp() - hour.timestamp()) / 60 < 5:
        return True

    if Zipcode.query.count() == 0:
        return True

    logger.info("Skipping geonames sync because the timestamp is %s", now.timestamp())
    return False


@celery.task()
def models_sync(force_rebuild_geography: typing.Optional[bool]):
    logger = get_celery_logger()
    start_ts = time.perf_counter()
    if force_rebuild_geography is None:
        force_rebuild_geography = _should_sync_geonames()
    if force_rebuild_geography:
        geonames_sync()
    purpleair_sync()
    end_ts = time.perf_counter()
    logger.info("Completed models_sync in %s seconds", end_ts - start_ts)
