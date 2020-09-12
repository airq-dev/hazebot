import html

from airq.commands.base import ApiCommand
from airq.commands.base import CommandContext
from airq.commands.invalid import InvalidInput
from airq.commands.menu import ShowMenu
from airq.commands.quality import GetQuality
from airq.models.requests import ClientIdentifierType


def _parse_command(ctx: CommandContext) -> ApiCommand:
    for command_type in (ShowMenu, GetQuality):
        command = command_type.parse(ctx)
        if command:
            return command
    return InvalidInput(ctx)


def handle_command(
    user_input: str, identifier: str, identifier_type: ClientIdentifierType
) -> str:
    ctx = CommandContext(
        user_input=user_input, identifier=identifier, identifier_type=identifier_type
    )

    message = _parse_command(ctx).handle()

    if identifier_type == ClientIdentifierType.IP:
        message = [html.escape(m) for m in message]
        separator = "<br>"
    else:
        separator = "\n"

    return separator.join(message)
