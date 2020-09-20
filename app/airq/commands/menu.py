import typing

from airq.commands.base import ApiCommandHandler
from airq.models.messages import MessageType


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
        self._persist_message(MessageType.MENU)
        return message
