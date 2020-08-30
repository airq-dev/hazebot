import collections

from airq import airnow


class Forecast:
    def __init__(self, air_quality, category_number):
        self.air_quality = air_quality
        self.category_number = category_number

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


def get_forecast_for_zipcode(zipcode):
    response = airnow.get_by_zipcode(zipcode)
    if response is not None:
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
            return Forecast(average_aqi, aqi_categories.most_common(1)[0][0])
