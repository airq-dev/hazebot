from flask_babel import gettext

from airq.commands.base import MessageResponse
from airq.commands.base import RegexCommand
from airq.models.events import EventType


class ShowAbout(RegexCommand):
    pattern = r"^4[\.\)]?$"

    def handle(self) -> MessageResponse:
        self.client.log_event(EventType.ABOUT)
        return MessageResponse(
            body=gettext(
                "hazebot runs on PurpleAir sensor data and is a free service. Reach us at hazebot.org or info@hazebot.org. Press 7 for information on how to support our work."
            )
        )
