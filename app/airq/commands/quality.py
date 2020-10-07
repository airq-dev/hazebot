import abc
import typing

from flask_babel import ngettext, gettext

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
                    gettext(
                        "Hmm. Are you sure %(zipcode)s is a valid US zipcode?",
                        zipcode=self.params["zipcode"]
                    )
                ]
        else:
            if self.client.zipcode is None:
                return self._get_missing_zipcode_message()
            zipcode = self.client.zipcode

        if not zipcode.pm25 or zipcode.is_pm25_stale:
            return [
                gettext(
                    'Oops! We couldn\'t determine the air quality for "%(zipcode)s". Please try a different zip code.',
                    zipcode=zipcode.zipcode
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
        aqi_display = gettext(" (AQI $(aqi)s)", aqi) if aqi else ""
        message.append(
            gettext(
                    "%(city)s %(ziipcode)s is %(pm25_level)s%(aqi_display)s.",
                    city=zipcode.city.name,
                    zipcode=zipcode.zipcode,
                    pm25_level=zipcode.pm25_level.display,
                    aqi_display=aqi_display
                )
            )
        )

        has_zipcode = self.client.zipcode_id is not None
        was_updated = self.client.update_subscription(zipcode)
        if not self.client.is_enabled_for_alerts:
            message.append("")
            message.append(
                gettext('Alerting is disabled. Text "Y" to re-enable alerts when air quality changes.')
            )
        elif was_updated:
            if has_zipcode:
                # Zipcode changed.
                message.append("")
                message.append(gettext(
                    "You are now receiving alerts for $(zipcode)s.",
                    zipcode=zipcode.zipcode
                ))
            else:
                tasks.send_intro_message.apply_async((self.client.id,), countdown=5)
        else:
            message.append("")
            message.append(gettext('Text "M" for Menu, "E" to end alerts.'))

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
            message.append(gettext("Here are the closest places with better air quality:"))
            for recommendation in recommended_zipcodes:
                message.append(
                    gettext(" - %(city)s %(zipcode)s: %(pm25_level)s (%(distance)f mi)",
                        city=recommendation.city.name,
                        zipcode=recommendation.zipcode,
                        pm25_level=recommendation.pm25_level.display.upper(),
                        distance=round(
                            kilometers_to_miles(recommendation.distance(zipcode)),
                            ndigits=1,
                        ),  # TODO: Make this based on locale
                    )
                )
            message.append("")

        message.append(
            ngettext(
                "Average PM2.5 from %(num_sensors)d sensor near %(zipcode)s is %(pm25)s ug/m^3.",
                "Average PM2.5 from %(num_sensors)d sensors near %(zipcode)s is %(pm25)s ug/m^3.",
                num_sensors=zipcode.num_sensors,
                zipcode=zipcode.zipcode,
                pm25=zipcode.pm25,
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
