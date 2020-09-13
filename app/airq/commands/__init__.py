import html

from airq.commands.invalid import InvalidInputHandler
from airq.commands.menu import ShowMenuHandler
from airq.commands.quality import GetQualityHandler
from airq.models.clients import Client
from airq.models.clients import ClientIdentifierType


ROUTES = [
    ShowMenuHandler.route(pattern=r"^m$"),
    GetQualityHandler.route(pattern=r"^(?P<zipcode>\d{5})$"),
    GetQualityHandler.route(
        pattern=r"^d(?:\s(?P<zipcode>\d{5}))?$", mode=GetQuality.Mode.DETAILS
    ),
    GetQualityHandler.route(
        pattern=r"^r(?:\s(?P<zipcode>\d{5}))?$", mode=GetQuality.Mode.RECOMMEND
    ),
    GetQualityHandler.route(pattern=r"^l$"),
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
