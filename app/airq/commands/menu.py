from flask_babel import gettext

from airq.commands.base import MessageResponse
from airq.commands.base import RegexCommand
from airq.models.events import EventType


class ShowMenu(RegexCommand):
    pattern = r"^(m|menu)$"

    def handle(self) -> MessageResponse:
        self.client.log_event(EventType.MENU)
        return MessageResponse.from_strings(
            [
                gettext("Reply"),
                gettext("1. Details and recommendations"),
                gettext("2. Current AQI"),
                gettext("3. Hazebot info"),
                gettext("4. Give feedback"),
                gettext("5. Stop alerts"),
                "",
                gettext("Or, enter a new zipcode."),
            ]
        )
