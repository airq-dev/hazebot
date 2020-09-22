import typing

from airq.commands.base import ApiCommandHandler
from airq.models.zipcodes import Zipcode


class UnsubscribeHandler(ApiCommandHandler):
    def handle(self) -> typing.List[str]:
        if self.client.zipcode is None:
            return self._get_missing_zipcode_message()

        if self.client.alerts_disabled_at:
            return [
                f"Looks like you already stopped watching {self.client.zipcode.zipcode}."
            ]

        self.client.disable_alerts()

        return [
            f"Got it! You will no longer recieve alerts for {self.client.zipcode.zipcode}. Text another zipcode if you'd like updates or reply M for menu."
        ]
