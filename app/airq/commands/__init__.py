import html

from airq.commands.invalid import InvalidInputHandler
from airq.commands.about import ShowAboutHandler
from airq.commands.feedback import ShowFeedbackHandler
from airq.commands.feedback import RecieveFeedbackHandler
from airq.commands.menu import ShowMenuHandler
from airq.commands.quality import GetDetailsHandler
from airq.commands.quality import GetQualityHandler
from airq.commands.stop import StopHandler
from airq.models.clients import Client
from airq.models.clients import ClientIdentifierType
from airq.models.events import EventType

ZIPCODE_REGEX = "(?P<raw_zip>\d{5})"
MATCH_NONE_REGEX = r"a^"

ROUTES = [
    GetQualityHandler.route(pattern=r"^{}$".format(ZIPCODE_REGEX)),
    GetDetailsHandler.route(pattern=r"^1[\.\)]?$"),
    GetQualityHandler.route(pattern=r"^2[\.\)]?$"),
    ShowAboutHandler.route(pattern=r"^3[\.\)]?$"),
    ShowFeedbackHandler.route(pattern=r"^4[\.\)]?$"),
    RecieveFeedbackHandler.route(pattern=MATCH_NONE_REGEX),
    ShowMenuHandler.route(pattern=r"^m$"),
    StopHandler.route(pattern=r"^u$"),
]


def handle_command(
    user_input: str, identifier: str, identifier_type: ClientIdentifierType
) -> str:
    client, was_created = Client.query.get_or_create(identifier, identifier_type)
    if not was_created:
        client.mark_seen()

    for route in ROUTES:
        match = route.match(user_input)
        if match:
            message = route.handle(client, user_input, **match.groupdict())
            break
        elif route.factory.should_handle(route.pattern, client, user_input):
            message = route.handle(client, user_input)
            break
    else:
        message = InvalidInputHandler(client, user_input).handle()

    if identifier_type == ClientIdentifierType.IP:
        message = [html.escape(s) for s in message]
        separator = "<br>"
    else:
        separator = "\n"

    return separator.join(message)
