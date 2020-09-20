import typing

from airq.commands.base import ApiCommandHandler
from airq.models.messages import MessageType
from airq.models.zipcodes import Zipcode


class StopHandler(ApiCommandHandler):
    def handle(self) -> typing.List[str]:
        if self.client.zipcode is None:
            return [
                "Looks like you haven't use hazebot before! Please text us a zipcode and we'll send you the air quality."
            ]

        if self.client.alerts_disabled_at:
            return [
                f"Looks like you already stopped watching {self.client.zipcode.zipcode}."
            ]

        self.client.disable_alerts()
        self._persist_message(
            MessageType.UNSUBSCRIBE, zipcode=self.client.zipcode.zipcode
        )
        return [
            f"Got it! You will no longer recieve alerts for {self.client.zipcode.zipcode}. Text another zipcode if you'd like updates or reply M for menu."
        ]
