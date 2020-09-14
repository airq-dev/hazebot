import html

from airq.commands.invalid import InvalidInputHandler
from airq.commands.about import ShowAboutHandler
from airq.commands.menu import ShowMenuHandler
from airq.commands.quality import GetQualityHandler
from airq.commands.stop import StopHandler
from airq.commands.watch import WatchHandler
from airq.models.clients import Client
from airq.models.clients import ClientIdentifierType


ZIPCODE_REGEX = "(?P<zipcode>\d{5})"


ROUTES = [
    GetQualityHandler.route(pattern=r"^{}$".format(ZIPCODE_REGEX)),
    GetQualityHandler.route(
        pattern=r"^d(?:\s{})?$".format(ZIPCODE_REGEX),
        mode=GetQualityHandler.Mode.DETAILS,
    ),
    GetQualityHandler.route(pattern=r"^l$"),
    GetQualityHandler.route(
        pattern=r"^r(?:\s{})?$".format(ZIPCODE_REGEX),
        mode=GetQualityHandler.Mode.RECOMMEND,
    ),
    ShowAboutHandler.route(pattern=r"^\?$"),
    ShowMenuHandler.route(pattern=r"^m$"),
    StopHandler.route(pattern=r"^s$"),
    StopHandler.route(pattern=r"^u$", stop_all=True),
    WatchHandler.route(pattern=r"^w(?:\s{})?$".format(ZIPCODE_REGEX)),
]


def handle_command(
    user_input: str, identifier: str, identifier_type: ClientIdentifierType
) -> str:
    client = Client.get_or_create(identifier, identifier_type)

    for route in ROUTES:
        match = route.match(user_input)
        if match:
            message = route.handle(client, user_input, **match.groupdict())
            break
    else:
        message = InvalidInputHandler(client, user_input).handle()

    if identifier_type == ClientIdentifierType.IP:
        message = [html.escape(s) for s in message]
        separator = "<br>"
    else:
        separator = "\n"

    return separator.join(message)
