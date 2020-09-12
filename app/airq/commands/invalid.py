import typing

from airq.commands.base import ApiCommand
from airq.commands.base import CommandContext


class InvalidInput(ApiCommand):
    @classmethod
    def parse(cls, ctx: CommandContext) -> typing.Optional["ApiCommand"]:
        return cls(ctx)

    def handle(self) -> typing.List[str]:
        message = [
            f'Unrecognized option "{self.ctx.user_input}". Try one of these: ',
            "",
        ]
        message.extend(self._get_menu())
        return message
