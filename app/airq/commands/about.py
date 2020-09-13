import typing

from airq.commands.base import ApiCommand
from airq.commands.base import CommandContext


class ShowAbout(ApiCommand):
    @classmethod
    def parse(cls, ctx: CommandContext) -> typing.Optional["ApiCommand"]:
        user_input = ctx.user_input.split()
        if len(user_input) == 1 and user_input[0].lower() == "i":
            return cls(ctx)
        return None

    def handle(self) -> typing.List[str]:
        return [
            "hazebot runs on PurpleAir sensor data and is a free text service designed to provide accessible local air quality information. Visit hazebot.org to learn more."
        ]
