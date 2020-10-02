import html
import typing

from airq.commands.base import SMSCommand
from airq.commands.about import ShowAbout
from airq.commands.invalid import InvalidInput
from airq.commands.feedback import ReceiveFeedback
from airq.commands.feedback import ShowFeedback
from airq.commands.menu import ShowMenu
from airq.commands.quality import GetDetails
from airq.commands.quality import GetLast
from airq.commands.quality import GetQuality
from airq.commands.resubscribe import Resubscribe
from airq.commands.unsubscribe import Unsubscribe
from airq.models.clients import Client
from airq.models.clients import ClientIdentifierType


COMMANDS: typing.List[typing.Type[SMSCommand]] = [
    #
    # Commands which should always take precedence come first
    #
    GetQuality,
    ShowMenu,
    #
    # ReceiveFeedback needs to come before numbered commands because it interprets
    # certain input (e.g., "1") as selecting an option instead of choosing a command.
    #
    ReceiveFeedback,
    #
    # The "regular" (number-based) commands come next. Order does not matter for these.
    #
    GetDetails,
    GetLast,
    Resubscribe,
    ShowAbout,
    ShowFeedback,
    Unsubscribe,
]


def _parse_command(client: Client, user_input: str) -> SMSCommand:
    for cmd_type in COMMANDS:
        cmd = cmd_type(client, user_input)
        if cmd.should_handle():
            return cmd

    return InvalidInput(client, user_input)


def handle_command(
    user_input: str, identifier: str, identifier_type: ClientIdentifierType
) -> str:
    client, was_created = Client.query.get_or_create(identifier, identifier_type)
    if not was_created:
        client.mark_seen()

    message = _parse_command(client, user_input).handle()

    if identifier_type == ClientIdentifierType.IP:
        message = [html.escape(s) for s in message]
        separator = "<br>"
    else:
        separator = "\n"

    return separator.join(message)
