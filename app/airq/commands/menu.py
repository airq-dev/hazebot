import typing

from flask_babel import gettext

from airq.commands.base import RegexCommand
from airq.models.events import EventType


class ShowMenu(RegexCommand):
    pattern = r"^(m|menu)$"

    def handle(self) -> typing.List[str]:
        self.client.log_event(EventType.MENU)
        return [
            "Reply",
            "1. Details and recommendations",
            "2. Current AQI",
            "3. Hazebot info",
            "4. Give feedback",
            "5. Stop alerts",
            "",
            "Or, enter a new zipcode.",
        ]
