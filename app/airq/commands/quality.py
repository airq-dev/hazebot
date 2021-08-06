import abc

from flask_babel import ngettext, gettext

from airq import config
from airq.commands.base import MessageResponse
from airq.commands.base import RegexCommand
from airq.lib.geo import kilometers_to_miles
from airq.models.events import EventType
from airq.models.zipcodes import Zipcode


class BaseQualityCommand(RegexCommand):
    def handle(self) -> MessageResponse:
        if self.params.get("zipcode"):
            zipcode = Zipcode.query.get_by_zipcode(self.params["zipcode"])
            if zipcode is None:
                return MessageResponse(
                    body=gettext(
                        "Hmm. Are you sure %(zipcode)s is a valid US zipcode?",
                        zipcode=self.params["zipcode"],
                    )
                )
        else:
            if self.client.zipcode is None:
                return self._get_missing_zipcode_message()
            zipcode = self.client.zipcode

        if not zipcode.pm25 or zipcode.is_pm25_stale:
            return MessageResponse(
                body=gettext(
                    'Oops! We couldn\'t determine the air quality for "%(zipcode)s". Please try a different zip code.',
                    zipcode=zipcode.zipcode,
                )
            )

        return self._get_message(zipcode)

    @abc.abstractmethod
    def _get_message(self, zipcode: Zipcode) -> MessageResponse:
        ...


class GetQuality(BaseQualityCommand):
    pattern = r"^(?P<zipcode>\d{5})$"
    event_type = EventType.QUALITY

    def _get_message(self, zipcode: Zipcode) -> MessageResponse:
        is_first_message = self.client.zipcode_id is None
        was_updated = self.client.update_subscription(zipcode)

        aqi_display = gettext(" (AQI %(aqi)s)", aqi=self.client.get_current_aqi())

        if self.client.is_enabled_for_alerts and is_first_message and was_updated:
            response = (
                MessageResponse()
                .write(
                    gettext(
                        "Welcome to Hazebot! We'll send you alerts when air quality in %(city)s %(zipcode)s changes category. Air quality is now %(pm25_level)s%(aqi_display)s.",
                        city=zipcode.city.name,
                        zipcode=zipcode.zipcode,
                        pm25_level=self.client.get_current_pm25_level().display,
                        aqi_display=aqi_display,
                    )
                )
                .newline()
                .write(
                    gettext(
                        'Save this contact and text us your zipcode whenever you\'d like an instant update. And you can always text "M" to see the whole menu.'
                    )
                )
                .media(
                    f"{config.SERVER_URL}/public/vcard/{self.client.locale}.vcf",
                )
            )
        else:
            response = (
                MessageResponse()
                .write(
                    gettext(
                        "%(city)s %(zipcode)s is %(pm25_level)s%(aqi_display)s.",
                        city=zipcode.city.name,
                        zipcode=zipcode.zipcode,
                        pm25_level=self.client.get_current_pm25_level().display,
                        aqi_display=aqi_display,
                    )
                )
                .newline()
            )
            if not self.client.is_enabled_for_alerts:
                response.write(
                    gettext(
                        'Alerting is disabled. Text "Y" to re-enable alerts when air quality changes.'
                    )
                )
            elif was_updated:
                response.write(
                    gettext(
                        "You are now receiving alerts for %(zipcode)s.",
                        zipcode=zipcode.zipcode,
                    )
                )
            else:
                response.write(gettext('Text "M" for Menu, "E" to end alerts.'))

        self.client.log_event(
            self.event_type,
            zipcode=zipcode.zipcode,
            pm25=self.client.get_current_pm25(),
        )

        return response


class GetLast(GetQuality):
    pattern = r"^2[\.\)]?$"
    event_type = EventType.LAST


class GetDetails(BaseQualityCommand):
    pattern = r"^1[\.\)]?$"

    def _get_message(self, _zipcode: Zipcode) -> MessageResponse:
        response = (
            MessageResponse()
            .write(self.client.get_current_pm25_level().description)
            .write("")
        )

        num_desired = 3
        recommended_zipcodes = self.client.get_recommendations(num_desired)
        if recommended_zipcodes:
            response.write(
                gettext("Here are the closest places with better air quality:")
            )
            conversion_factor = self.client.conversion_factor
            for recommendation in recommended_zipcodes:
                response.write(
                    gettext(
                        " - %(city)s %(zipcode)s: %(pm25_level)s (%(distance)s mi)",
                        city=recommendation.city.name,
                        zipcode=recommendation.zipcode,
                        pm25_level=recommendation.get_pm25_level(
                            conversion_factor
                        ).display.upper(),
                        distance=round(
                            kilometers_to_miles(
                                recommendation.distance(self.client.zipcode)
                            ),
                            ndigits=1,
                        ),  # TODO: Make this based on locale
                    )
                )
            response.newline()

        response.write(
            ngettext(
                "Average PM2.5 from %(num)d sensor near %(zipcode)s is %(pm25)s ug/m^3.",
                "Average PM2.5 from %(num)d sensors near %(zipcode)s is %(pm25)s ug/m^3.",
                self.client.zipcode.num_sensors,
                zipcode=self.client.zipcode.zipcode,
                pm25=self.client.get_current_pm25(),
            )
        )

        self.client.log_event(
            EventType.DETAILS,
            zipcode=self.client.zipcode.zipcode,
            recommendations=[r.zipcode for r in recommended_zipcodes],
            pm25=self.client.get_current_pm25(),
            num_sensors=self.client.zipcode.num_sensors,
        )

        return response
