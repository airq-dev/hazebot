import typing

from airq.commands.base import RegexCommand
from airq.models.events import EventType


class ShowMenu(RegexCommand):
    pattern = r"^m$"

    def handle(self) -> typing.List[str]:
        self.client.log_event(EventType.MENU)
        return [
            "Reply",
            "1. Details and recommendations",
            "2. Current AQI",
            "3. Hazebot info",
            "4. Give feedback",
            "",
            "Or, enter a new zipcode.",
        ]
