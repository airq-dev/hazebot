import abc
import typing

from flask_babel import gettext

from airq.commands.base import RegexCommand
from airq.lib.geo import kilometers_to_miles
from airq.models.events import EventType
from airq.models.zipcodes import Zipcode


class BaseQualityCommand(RegexCommand):
    def handle(self) -> typing.List[str]:
        if self.params.get("zipcode"):
            zipcode = Zipcode.query.get_by_zipcode(self.params["zipcode"])
            if zipcode is None:
                return [
                    "Hmm. Are you sure {} is a valid US zipcode?".format(
                        self.params["zipcode"]
                    )
                ]
        else:
            if self.client.zipcode is None:
                return self._get_missing_zipcode_message()
            zipcode = self.client.zipcode

        if not zipcode.pm25 or zipcode.is_pm25_stale:
            return [
                'Oops! We couldn\'t determine the air quality for "{}". Please try a different zip code.'.format(
                    zipcode.zipcode
                )
            ]

        message = self._get_message(zipcode)

        self.client.log_request(zipcode)

        return message

    @abc.abstractmethod
    def _get_message(self, zipcode: Zipcode) -> typing.List[str]:
        ...


class GetQuality(BaseQualityCommand):
    zipcode_regex = r"(?P<zipcode>\d{5})"
    repeat_regex = r"(?:2[\.\)]?)"
    pattern = r"^(?:{}|{})$".format(zipcode_regex, repeat_regex)

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
        if not self.client.is_enabled_for_alerts:
            message.append("")
            message.append(
                'Alerting is disabled. Text "Y" to re-enable alerts when air quality changes.'
            )
        elif was_updated:
            message.append("")
            message.append("We'll alert you when the air quality changes category.")
            message.append("Reply M for menu, U to stop this alert.")

        if self.user_input == "2":
            type_code = EventType.LAST
        else:
            type_code = EventType.QUALITY
        self.client.log_event(type_code, zipcode=zipcode.zipcode, pm25=zipcode.pm25)

        return message


class GetDetails(BaseQualityCommand):
    pattern = r"^1[\.\)]?$"

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
                        round(
                            kilometers_to_miles(recommendation.distance(zipcode)),
                            ndigits=1,
                        ),  # TODO: Make this based on locale
                    )
                )
            message.append("")

        message.append(
            "Average PM2.5 from {} sensor(s) near {} is {} ug/m^3.".format(
                zipcode.num_sensors,
                zipcode.zipcode,
                zipcode.pm25,
            )
        )

        self.client.log_event(
            EventType.DETAILS,
            zipcode=zipcode.zipcode,
            recommendations=[r.zipcode for r in recommended_zipcodes],
            pm25=zipcode.pm25,
            num_sensors=zipcode.num_sensors,
        )

        return message
