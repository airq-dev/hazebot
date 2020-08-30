import collections
import datetime

from airq import airnow


FORECASTS = {}


class Forecast:
    def __init__(self, air_quality, category_number, recorded_at=None):
        self.air_quality = air_quality
        self.category_number = category_number
        self.recorded_at = recorded_at or datetime.datetime.now()

    @property
    def category_name(self):
        if self.category_number == 1:
            return "Good"
        if self.category_number == 2:
            return "Moderate"
        if self.category_number == 3:
            return "Unhealthy for Sensitive Groups"
        if self.category_number == 4:
            return "Unhealthy"
        if self.category_number == 5:
            return "Very Unhealthy"
        if self.category_number == 6:
            return "Hazardous"
        if self.category_number == 7:
            return "Unavailable"

    @classmethod
    def from_airnow_response(cls, airnow_response):
        combined_aqi = 0
        total_forecasts = 0
        aqi_categories = collections.Counter()
        for datum in airnow_response:
            # -1 indicates that airnow doesn't know the AQI
            if datum["AQI"] != -1:
                aqi_categories[datum["Category"]["Number"]] += 1
                combined_aqi += datum["AQI"]
                total_forecasts += 1
        if total_forecasts:
            average_aqi = round(combined_aqi / total_forecasts)
            return cls(average_aqi, aqi_categories.most_common(1)[0][0])


def _get_forecast_for_zipcode(zipcode):
    if zipcode in FORECASTS:
        forecast = FORECASTS[zipcode]
        # Cache for 1 hour: https://docs.airnowapi.org/faq#caching
        if datetime.datetime.now() < forecast.recorded_at + datetime.timedelta(hours=1):
            return forecast

    response = airnow.get_by_zipcode(zipcode)
    if response is not None:
        FORECASTS[zipcode] = Forecast.from_airnow_response(response)
        return FORECASTS[zipcode]


def get_forecast_message_for_zipcode(zipcode):
    if zipcode.isdigit():
        forecast = _get_forecast_for_zipcode(zipcode)
        if forecast:
            return (
                "Air quality near {zipcode}:\n"
                "\n"
                "Summary: {category_name}\n"
                "Average AQI: {air_quality}\n"
            ).format(
                zipcode=zipcode,
                category_name=forecast.category_name,
                air_quality=forecast.air_quality,
            )

    return f'Oops! We couldn\'t determine the air quality for "{zipcode}". Please try a different zip code.'