import typing

from airq.commands.base import ApiCommandHandler


class ShowAboutHandler(ApiCommandHandler):
    def handle(self) -> typing.List[str]:
        return [
            "hazebot runs on PurpleAir sensor data and is a free text service designed to provide accessible local air quality information. Visit hazebot.org to learn more."
        ]
