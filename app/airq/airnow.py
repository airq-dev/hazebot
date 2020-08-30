import datetime
import logging
import os
import requests


logger = logging.getLogger(__name__)


AIRNOW_API_KEY = os.getenv("AIRNOW_API_KEY")


AIRNOW_BASE_URL = (
    "http://www.airnowapi.org/aq/forecast/zipCode/"
    "?format=application/json"
    "&zipCode={zipcode}"
    "&date={date}"
    "&distance={distance}"
    "&API_KEY={api_key}"
)


def _get_url(zipcode):
    return AIRNOW_BASE_URL.format(
        zipcode=zipcode,
        date=datetime.datetime.now().strftime("%Y-%m-%d"),
        distance=5,
        api_key=AIRNOW_API_KEY,
    )


def get_by_zipcode(zipcode):
    try:
        resp = requests.get(_get_url(zipcode))
        resp.raise_for_status()
    except requests.RequestException as e:
        logger.exception("Failed to retrieve data from airnow: %s", e)
        return
    else:
        resp_json = resp.json()
        logger.info("Airnow response: %s", resp_json)
        return resp_json
