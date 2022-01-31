import typing

from airq.commands.base import MessageResponse
from airq.commands.base import SMSCommand
from airq.commands.about import ShowAbout
from airq.commands.donate import ShowDonate
from airq.commands.invalid import InvalidInput
from airq.commands.feedback import ReceiveFeedback
from airq.commands.feedback import ShowFeedback
from airq.commands.menu import ShowMenu
from airq.commands.quality import GetDetails
from airq.commands.quality import GetLast
from airq.commands.quality import GetQuality
from airq.commands.prefs import ListPrefs
from airq.commands.prefs import RequestSetPref
from airq.commands.prefs import SetPref
from airq.commands.resubscribe import Resubscribe
from airq.commands.unsubscribe import Unsubscribe
from airq.config import app
from airq.models.clients import Client
from airq.models.clients import ClientIdentifierType


# TODO: Create a more robust system for describing command precedence,
# when to use nested commands, etc.
COMMANDS: typing.List[typing.Type[SMSCommand]] = [
    #
    # SetPref needs to come before numbered commands because it interprets
    # certain input (e.g., "0") as selecting an option instead of choosing a command.
    #
    SetPref,
    GetDetails,
    GetLast,
    GetQuality,
    ListPrefs,
    Resubscribe,
    ShowAbout,
    ShowFeedback,
    ShowDonate,
    ShowMenu,
    RequestSetPref,
    ReceiveFeedback,
    # Unsubscribe comes last because "E" unsubscribes, but certain nested commands use "E"
    # as an option. Therefore, putting this last means we won't accidentally unsub people
    # who are trying to enter one of these nested commands.
    Unsubscribe,
]


def _parse_command(client: Client, user_input: str) -> SMSCommand:
    for cmd_type in COMMANDS:
        cmd = cmd_type(client, user_input)
        if cmd.should_handle():
            return cmd

    return InvalidInput(client, user_input)


def handle_command(
    user_input: str, identifier: str, identifier_type: ClientIdentifierType, locale: str
) -> MessageResponse:
    if not app.config['HAZEBOT_ENABLED']:
        return MessageResponse("Hazebot is sleeping until fire season. We'll be back in June or July of 2022.")
    else:
        client, was_created = Client.query.get_or_create(
            identifier, identifier_type, locale
        )
        if not was_created:
            client.mark_seen(locale)
        return _parse_command(client, user_input).handle()
