import geohash
import json
import logging
import math
import requests
import typing

from flask_babel import force_locale

from airq.celery import get_celery_logger
from airq.config import app
from airq.config import db
from airq.lib.clock import now
from airq.lib.clock import timestamp
from airq.lib.geo import haversine_distance
from airq.lib.purpleair import call_purpleair_data_api
from airq.lib.purpleair import call_purpleair_sensors_api
from airq.lib.trie import Trie
from airq.lib.util import chunk_list
from airq.models.clients import Client
from airq.models.relations import SensorZipcodeRelation
from airq.models.sensors import Sensor
from airq.models.zipcodes import Zipcode
from airq.sync.purpleair import metrics


# Try to get at least 8 readings per zipcode.
DESIRED_NUM_READINGS = 8

# Allow any number of readings within 2.5km from the zipcode centroid.
DESIRED_READING_DISTANCE_KM = 2.5


def _get_purpleair_sensors_data() -> typing.List[typing.Dict[str, typing.Any]]:
    logger = get_celery_logger()
    try:
        response_dict = call_purpleair_sensors_api().json()
    except (requests.RequestException, json.JSONDecodeError) as e:
        # Send an email to an admin if data lags by more than 30 minutes.
        # Otherwise, just log a warning as most of these errors are
        # transient. In the future we might choose to retry on transient
        # failures, but it's not urgent since we will rerun the sync
        # every ten minutes anyway.
        last_updated_at = Sensor.query.get_last_updated_at()
        seconds_since_last_update = timestamp() - last_updated_at
        if seconds_since_last_update > 30 * 60:
            level = logging.ERROR
        else:
            level = logging.WARNING
        logger.log(
            level,
            "%s updating purpleair data: %s",
            type(e).__name__,
            e,
            exc_info=True,
        )
        return []
    else:
        fields = response_dict["fields"]
        channel_flags = response_dict["channel_flags"]
        data = []
        for sensor_data in response_dict["data"]:
            sensor_data = dict(zip(fields, sensor_data))
            try:
                sensor_data["channel_flags"] = channel_flags[
                    sensor_data["channel_flags"]
                ]
            except KeyError:
                pass
            data.append(sensor_data)
        return data


# TODO: Remove this once `pm_cf_1` is available via the sensors API.
def _get_purpleair_pm_cf_1_data():
    logger = get_celery_logger()
    data = {}
    try:
        response_dict = call_purpleair_data_api().json()
    except (requests.RequestException, json.JSONDecodeError) as e:
        logger.warning(
            "Failed to retrieve pm_cf_1 data: %s",
            e,
            exc_info=True,
        )
    else:
        fields = response_dict.get("fields")
        if fields:
            for raw_data in response_dict["data"]:
                zipped = dict(zip(fields, raw_data))
                pm_cf_1 = zipped["pm_cf_1"]
                if isinstance(pm_cf_1, float):
                    data[zipped["ID"]] = pm_cf_1
    return data


def _is_valid_reading(sensor_data: typing.Dict[str, typing.Any]) -> bool:
    if sensor_data["last_seen"] < timestamp() - (60 * 60):
        # Out of date / maybe dead
        return False
    if sensor_data["channel_flags"] != "Normal":
        # Flagged for an unusually high reading
        return False
    try:
        pm25 = float(sensor_data["pm2.5"])
    except (TypeError, ValueError):
        return False
    if math.isnan(pm25):
        # Purpleair can occasionally return NaN.
        # I wonder if this is a bug on their end.
        return False
    if pm25 <= 0 or pm25 > 1000:
        # Something is very wrong
        return False
    try:
        humidity = float(sensor_data["humidity"])
    except (TypeError, ValueError):
        return False
    if math.isnan(humidity):
        return False
    latitude = sensor_data["latitude"]
    longitude = sensor_data["longitude"]
    if latitude is None or longitude is None:
        return False

    return True


def _sensors_sync(
    purpleair_data: typing.List[typing.Dict[str, typing.Any]],
    purpleair_pm_cf_1_data: typing.Dict[int, float],
) -> typing.List[int]:
    logger = get_celery_logger()

    existing_sensor_map = {s.id: s for s in Sensor.query.all()}

    updates = []
    new_sensors = []
    moved_sensor_ids = []
    for result in purpleair_data:
        if _is_valid_reading(result):
            sensor = existing_sensor_map.get(result["sensor_index"])
            latitude = result["latitude"]
            longitude = result["longitude"]
            pm25 = float(result["pm2.5"])
            humidity = float(result["humidity"])

            pm_cf_1 = purpleair_pm_cf_1_data.get(result["sensor_index"])
            if pm_cf_1 is None:
                continue

            data: typing.Dict[str, typing.Any] = {
                "id": result["sensor_index"],
                "latest_reading": pm25,
                "humidity": humidity,
                "updated_at": result["last_seen"],
                "pm_cf_1": pm_cf_1,
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
                    coordinates=f"POINT({longitude} {latitude})",
                    **{f"geohash_bit_{i}": c for i, c in enumerate(gh, start=1)},
                )
                moved_sensor_ids.append(result["sensor_index"])
            elif sensor.coordinates is None:
                # Sensor wasn't moved, but we haven't filled in its coordinates field yet.
                data['coordinates'] = f"POINT({longitude} {latitude})"

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


def _relations_sync(moved_sensor_ids: typing.List[int]):
    logger = get_celery_logger()

    trie: Trie[Zipcode] = Trie()
    for zipcode in Zipcode.query.all():
        trie.insert(zipcode.geohash, zipcode)

    new_relations = []

    # Delete the old relations before rebuilding them
    deleted_relations_count = SensorZipcodeRelation.query.filter(
        SensorZipcodeRelation.sensor_id.in_(moved_sensor_ids)
    ).delete(synchronize_session=False)
    logger.info("Deleting %s relations", deleted_relations_count)

    sensors = Sensor.query.filter(Sensor.id.in_(moved_sensor_ids)).all()
    for sensor in sensors:
        gh = sensor.geohash
        latitude = sensor.latitude
        longitude = sensor.longitude
        done = False
        zipcode_ids: typing.Set[int] = set()
        # TODO: Use Postgres' native geolocation extension.
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
                data = {
                    "zipcode_id": zipcode_id,
                    "sensor_id": sensor.id,
                    "distance": distance,
                }
                new_relations.append(SensorZipcodeRelation(**data))
            gh = gh[:-1]

    if new_relations:
        logger.info("Creating %s relations", len(new_relations))
        for objs in chunk_list(new_relations):
            db.session.bulk_save_objects(objs)
            db.session.commit()


def _send_alerts():
    logger = get_celery_logger()
    num_sent = 0
    for client in Client.query.filter_eligible_for_sending().all():
        with force_locale(client.locale):
            try:
                if client.maybe_notify():
                    num_sent += 1
            except Exception as e:
                logger.exception("Failed to send alert to %s: %s", client, e)

    logger.info("Sent %s alerts", num_sent)


def _send_share_requests() -> int:
    num_sent = 0
    if app.config["HAZEBOT_SHARE_REQUESTS_ENABLED"]:
        logger = get_celery_logger()
        for client in Client.query.filter_eligible_for_share_requests().all():
            with force_locale(client.locale):
                try:
                    if client.request_share():
                        num_sent += 1
                except Exception as e:
                    logger.exception("Failed to request share from %s: %s", client, e)

        logger.info("Requests %s shares", num_sent)

    return num_sent


def purpleair_sync():
    logger = get_celery_logger()

    logger.info("Fetching sensor from purpleair")
    purpleair_data = _get_purpleair_sensors_data()
    purpleair_pm_cf_1_data = _get_purpleair_pm_cf_1_data()

    logger.info("Recieved %s sensors", len(purpleair_data))
    moved_sensor_ids = _sensors_sync(purpleair_data, purpleair_pm_cf_1_data)

    if moved_sensor_ids:
        logger.info("Syncing relations for %s sensors", len(moved_sensor_ids))
        _relations_sync(moved_sensor_ids)

    logger.info("Syncing metrics")
    metrics.update()

    logger.info("Sending alerts")
    _send_alerts()

    logger.info("Requesting shares")
    _send_share_requests()
