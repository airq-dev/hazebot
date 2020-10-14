from flask_babel import gettext

from airq.commands.base import MessageResponse
from airq.commands.base import RegexCommand
from airq.models.events import EventType


class ShowAbout(RegexCommand):
    pattern = r"^3[\.\)]?$"

    def handle(self) -> MessageResponse:
        self.client.log_event(EventType.ABOUT)
        return MessageResponse(
            body=gettext(
                "hazebot runs on PurpleAir sensor data and is a free service providing accessible local air quality information. Visit hazebot.org or email info@hazebot.org for feedback."
            )
        )
