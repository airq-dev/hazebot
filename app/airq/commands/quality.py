import abc
import typing

from airq import config
from airq import tasks
from airq.commands.base import RegexCommand
from airq.lib.geo import kilometers_to_miles
from airq.models.clients import Client
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
    pattern = r"^(?P<zipcode>\d{5})$"
    event_type = EventType.QUALITY

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

        has_zipcode = self.client.zipcode_id is not None
        was_updated = self.client.update_subscription(zipcode)
        if not self.client.is_enabled_for_alerts:
            message.append("")
            message.append(
                'Alerting is disabled. Text "Y" to re-enable alerts when air quality changes.'
            )
        elif was_updated:
            if has_zipcode:
                # Zipcode changed.
                message.append("")
                message.append(f"You are now receiving alerts for {zipcode.zipcode}.")
            else:
                tasks.send_intro_message.apply_async((self.client.id,), countdown=5)
        else:
            message.append("")
            message.append('Text "M" for Menu, "E" to end alerts.')

        self.client.log_event(
            self.event_type, zipcode=zipcode.zipcode, pm25=zipcode.pm25
        )

        return message


class GetLast(GetQuality):
    pattern = r"^2[\.\)]?$"
    event_type = EventType.LAST


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
