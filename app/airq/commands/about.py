import typing

from airq.commands.base import ApiCommandHandler
from airq.models.messages import MessageType


class ShowAboutHandler(ApiCommandHandler):
    def handle(self) -> typing.List[str]:
        message = [
            "hazebot runs on PurpleAir sensor data and is a free service providing accessible local air quality information. Visit hazebot.org or email info@hazebot.org for feedback."
        ]
        self._persist_message(MessageType.ABOUT)
        return message
