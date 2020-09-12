import collections
import geohash
import logging
import requests
import typing

from airq.config import db
from airq.lib.geo import haversine_distance
from airq.lib.trie import Trie
from airq.lib.util import chunk_list
from airq.models.relations import SensorZipcodeRelation
from airq.models.sensors import Sensor, is_valid_reading
from airq.models.zipcodes import Zipcode


logger = logging.getLogger(__name__)


TRelationsMap = typing.Dict[int, typing.Dict[int, float]]


PURPLEAIR_URL = "https://www.purpleair.com/json"


def _get_purpleair_data() -> typing.List[typing.Dict[str, typing.Any]]:
    try:
        resp = requests.get(PURPLEAIR_URL)
        resp.raise_for_status()
    except requests.RequestException:
        logger.exception("Error updating purpleair data")
        results = []
    else:
        results = resp.json().get("results", [])
    return results


def _build_relations_map() -> TRelationsMap:
    relations_map: TRelationsMap = collections.defaultdict(dict)
    for relation in SensorZipcodeRelation.query.all():
        relations_map[relation.sensor_id][relation.zipcode_id] = relation.distance
    return relations_map


def _sensors_sync(
    purpleair_data: typing.List[typing.Dict[str, typing.Any]],
    relations_map: TRelationsMap,
) -> typing.List[int]:
    existing_sensor_map = {s.id: s for s in Sensor.query.all()}

    updates = []
    new_sensors = []
    moved_sensor_ids = []
    for result in purpleair_data:
        if is_valid_reading(result):
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

    return moved_sensor_ids


def _relations_sync(moved_sensor_ids: typing.List[int], relations_map: TRelationsMap):
    trie: Trie[Zipcode] = Trie()
    for zipcode in Zipcode.query.all():
        trie.insert(zipcode.geohash, zipcode)

    new_relations = []
    updates = []

    sensors = Sensor.query.filter(Sensor.id.in_(moved_sensor_ids)).all()
    for sensor in sensors:
        gh = sensor.geohash
        latitude = sensor.latitude
        longitude = sensor.longitude
        done = False
        zipcode_ids: typing.Set[int] = set()
        while gh and not done:
            zipcodes = [
                zipcode for zipcode in trie.get(gh) if zipcode.id not in zipcode_ids
            ]

            for zipcode_id, distance in sorted(
                [
                    (
                        z.id,
                        haversine_distance(
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
            gh = gh[:-1]

    if new_relations:
        logger.info("Creating %s relations", len(new_relations))
        for objs in chunk_list(new_relations):
            db.session.bulk_save_objects(objs)
            db.session.commit()

    if updates:
        logger.info("Updating %s relations", len(updates))
        for mappings in chunk_list(updates):
            db.session.bulk_update_mappings(SensorZipcodeRelation, mappings)
            db.session.commit()


def purpleair_sync():
    logger.info("Fetching sensor from purpleair")
    purpleair_data = _get_purpleair_data()

    logger.info("Recieved %s sensors", len(purpleair_data))
    relations_map = _build_relations_map()
    moved_sensor_ids = _sensors_sync(purpleair_data, relations_map)

    if moved_sensor_ids:
        logger.info("Syncing relations for %s sensors", len(moved_sensor_ids))
        _relations_sync(moved_sensor_ids, relations_map)
