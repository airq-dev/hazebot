import collections
import datetime
import os
import requests
import typing

from airq.providers.base import Metrics, Provider, ProviderType


class AirnowProvider(Provider):
    TYPE = ProviderType.AIRNOW
    API_KEY = os.getenv("AIRNOW_API_KEY")
    BASE_URL = (
        "http://www.airnowapi.org/aq/forecast/zipCode/"
        "?format=application/json"
        "&zipCode={zipcode}"
        "&date={date}"
        "&distance={distance}"
        "&API_KEY={api_key}"
    )
    RADIUS = 5

    def _get_url(self, zipcode: str) -> str:
        return self.BASE_URL.format(
            zipcode=zipcode,
            date=datetime.datetime.now().strftime("%Y-%m-%d"),
            distance=self.RADIUS,
            api_key=self.API_KEY,
        )

    def _get_by_zipcode(self, zipcode: str) -> typing.List[dict]:
        try:
            resp = requests.get(self._get_url(zipcode))
            resp.raise_for_status()
        except requests.RequestException as e:
            self.logger.exception("Failed to retrieve data from airnow: %s", e)
            return []
        else:
            resp_json = resp.json()
            self.logger.info("Airnow response: %s", resp_json)
            return resp_json

    def get_metrics(self, zipcode: str) -> typing.Optional[Metrics]:
        response = self._get_by_zipcode(zipcode)
        if not response:
            return None

        combined_aqi = 0
        total_forecasts = 0
        aqi_categories: typing.Counter[int] = collections.Counter()
        category_number_to_category_name = {}
        for datum in response:
            # -1 indicates that airnow doesn't know the AQI
            if datum["AQI"] != -1:
                aqi_categories[datum["Category"]["Number"]] += 1
                category_number_to_category_name[datum["Category"]["Number"]] = datum[
                    "Category"
                ]["Name"]
                combined_aqi += datum["AQI"]
                total_forecasts += 1

        if not total_forecasts:
            return None

        average_aqi = round(combined_aqi / total_forecasts)
        category_number = aqi_categories.most_common(1)[0][0]
        category_name = category_number_to_category_name[category_number]
        return self._generate_metrics(
            [
                ("Summary", category_name),
                ("Average AQI", average_aqi),
                ("Radius", f"{self.RADIUS} miles"),
            ],
            zipcode,
        )
