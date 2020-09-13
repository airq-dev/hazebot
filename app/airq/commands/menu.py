import typing

from airq.commands.base import ApiCommand
from airq.commands.base import CommandContext


class ShowMenu(ApiCommand):
    @classmethod
    def parse(cls, ctx: CommandContext) -> typing.Optional["ApiCommand"]:
        user_input = ctx.user_input.split()
        if len(user_input) == 1 and user_input[0].lower() == "m":
            return cls(ctx)
        return None

    def handle(self) -> typing.List[str]:
        return self._get_menu()
