import logging
import requests
import typing


logger = logging.getLogger(__name__)


class ApiException(Exception):
    pass


def get_readings(sensor_ids: typing.Set[int]) -> typing.Dict[int, float]:
    logger.info(
        "Retrieving pm25 data from purpleair for %s sensors: %s",
        len(sensor_ids),
        sensor_ids,
    )

    readings = {}

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
        for r in resp.json().get("results"):
            if not r.get("ParentID"):
                sensor_id = r["ID"]
                pm25 = float(r.get("PM2_5Value", 0))
                readings[sensor_id] = pm25

    return readings
