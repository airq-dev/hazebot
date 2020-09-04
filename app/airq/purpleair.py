import logging
import requests
import typing

from airq import cache


logger = logging.getLogger(__name__)


class ApiException(Exception):
    pass


def get_readings(sensor_ids: typing.Set[int]) -> typing.Dict[int, float]:
    logger.info(
        "Retrieving pm25 data from purpleair for %s sensors: %s",
        len(sensor_ids),
        sensor_ids,
    )

    live_sensors = {}

    try:
        resp = requests.get(
            "https://www.purpleair.com/json?show={}".format(
                "|".join(map(str, sensor_ids))
            )
        )
        resp.raise_for_status()
    except requests.RequestException as e:
        logger.exception(
            "Error retrieving data for sensors %s: %s", sensor_ids, e,
        )
    else:
        dead_sensors = {}
        for r in resp.json().get("results"):
            if not r.get("ParentID"):
                sensor_id = r["ID"]
                pm25 = float(r.get("PM2_5Value", 0))
                if pm25 <= 0 or pm25 > 500:
                    logger.warning(
                        "Marking sensor %s dead because its pm25 is %s",
                        sensor_id,
                        pm25,
                    )
                    dead_sensors[sensor_id] = True
                else:
                    sensor_ids.remove(sensor_id)
                    live_sensors[sensor_id] = pm25

        if dead_sensors:
            cache.DEAD_SENSORS.set_many(dead_sensors)

        if live_sensors:
            cache.PM25.set_many(live_sensors)

        if sensor_ids:
            # This should be empty now if we've gotten pm25 info for every sensor.
            logger.warning("No results for ids: %s", sensor_ids)

    return live_sensors
