import typing

from airq.commands.base import ApiCommandHandler
from airq.models.events import EventType


class ShowMenuHandler(ApiCommandHandler):
    def handle(self) -> typing.List[str]:
        message = [
            "Reply",
            "1. Details and recommendations",
            "2. Current AQI",
            "3. Hazebot info",
            "",
            "Or, enter a new zipcode.",
        ]
        self.client.log_event(EventType.MENU)
        return message
