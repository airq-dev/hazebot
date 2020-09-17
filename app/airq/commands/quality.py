import abc
import typing

from airq.commands.base import ApiCommandHandler
from airq.lib.geo import kilometers_to_miles
from airq.models.zipcodes import Zipcode


class BaseQualityHandler(ApiCommandHandler):
    def handle(self, raw_zip: typing.Optional[str] = None) -> typing.List[str]:
        if raw_zip:
            zipcode = Zipcode.get_by_zipcode(raw_zip)
            if zipcode is None:
                return [f"Hmm. Are you sure {raw_zip} is a valid US zipcode?"]
        else:
            if self.client.zipcode is None:
                return [
                    "Looks like you haven't use hazebot before! Please text us a zipcode and we'll send you the air quality"
                ]
            zipcode = self.client.zipcode

        # Mypy gets really confused here, tell it what's what.
        assert zipcode is not None, "Zipcode unexpectedly None"

        if not zipcode.pm25 or zipcode.is_pm25_stale:
            return [
                f'Oops! We couldn\'t determine the air quality for "{zipcode.zipcode}". Please try a different zip code.'
            ]

        message = self._get_message(zipcode)

        self.client.log_request(zipcode)

        return message

    @abc.abstractmethod
    def _get_message(self, zipcode: Zipcode) -> typing.List[str]:
        ...


class GetQualityHandler(BaseQualityHandler):
    def _get_message(self, zipcode: Zipcode) -> typing.List[str]:
        message = []
        aqi = zipcode.aqi
        message.append(
            "{} {} is {}{}.".format(
                zipcode.city.name,
                zipcode.zipcode,
                zipcode.pm25_level.display,
                f" (AQI {aqi})" if aqi else "",
            )
        )
        was_updated = self.client.update_subscription(zipcode)
        if was_updated:
            message.append("")
            message.append("We'll alert you when the air quality changes category.")
            message.append("Reply M for menu, U to stop this alert.")
        return message


class GetDetailsHandler(BaseQualityHandler):
    def _get_message(self, zipcode: Zipcode) -> typing.List[str]:
        message = []
        message.append(zipcode.pm25_level.description)
        message.append("")

        num_desired = 3
        recommended_zipcodes = zipcode.get_recommendations(num_desired)
        if recommended_zipcodes:
            message.append("Here are the closest places with better air quality:")
            for recommendation in recommended_zipcodes:
                message.append(
                    " - {} {}: {} ({} mi)".format(
                        recommendation.city.name,
                        recommendation.zipcode,
                        recommendation.pm25_level.display.upper(),
                        round(kilometers_to_miles(recommendation.distance(zipcode)), 1),
                    )
                )
            message.append("")

        message.append(
            f"Average PM2.5 from {zipcode.num_sensors} sensor(s) near {zipcode.zipcode} is {zipcode.pm25} ug/m^3."
        )

        return message
