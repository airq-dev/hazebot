import typing

from airq.commands.base import ApiCommandHandler


class ShowMenuHandler(ApiCommandHandler):
    def handle(self) -> typing.List[str]:
        return [
            "Reply",
            "1. Details and recommendations",
            "2. Current AQI",
            "3. Hazebot info",
            "",
            "Or, enter a new zipcode.",
        ]
