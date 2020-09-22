import typing

from airq.commands.base import ApiCommandHandler
from airq.models.events import EventType


class ShowAboutHandler(ApiCommandHandler):
    def handle(self) -> typing.List[str]:
        message = [
            "hazebot runs on PurpleAir sensor data and is a free service providing accessible local air quality information. Visit hazebot.org or email info@hazebot.org for feedback."
        ]
        self.client.log_event(EventType.ABOUT)
        return message
