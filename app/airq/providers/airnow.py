import collections
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


def _get_by_zipcode(zipcode):
    try:
        resp = requests.get(_get_url(zipcode))
        resp.raise_for_status()
    except requests.RequestException as e:
        logger.exception("Failed to retrieve data from airnow: %s", e)
    else:
        resp_json = resp.json()
        logger.info("Airnow response: %s", resp_json)
        return resp_json


def get_message_for_zipcode(zipcode):
    response = _get_by_zipcode(zipcode)
    if response is not None:
        combined_aqi = 0
        total_forecasts = 0
        aqi_categories = collections.Counter()
        category_number_to_category_name = {}
        for datum in response:
            # -1 indicates that airnow doesn't know the AQI
            if datum["AQI"] != -1:
                aqi_categories[datum["Category"]["Number"]] += 1
                category_number_to_category_name[datum["Category"]["Number"]] = datum['Category']['Name']
                combined_aqi += datum["AQI"]
                total_forecasts += 1
        if total_forecasts:
            average_aqi = round(combined_aqi / total_forecasts)
            category_number = aqi_categories.most_common(1)[0][0]
            category_name = category_number_to_category_name[category_number]
            return (
                "Air quality near {zipcode}:\n"
                "\n"
                "Summary: {category_name}\n"
                "Average AQI: {air_quality}\n"
            ).format(
                zipcode=zipcode,
                category_name=category_name,
                air_quality=average_aqi,
            )
