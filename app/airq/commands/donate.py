from flask_babel import gettext

from airq.commands.base import MessageResponse
from airq.commands.base import RegexCommand
from airq.models.events import EventType


class ShowDonate(RegexCommand):
    pattern = r"^7[\.\)]?$"

    def handle(self) -> MessageResponse:
        self.client.log_event(EventType.DONATE)
        return MessageResponse(
            body=gettext(
                "Like this project? A few dollars allows hundreds of people to breathe easy with hazebot. Help us reach more by donating here: https://bit.ly/3bh0Cx9."
            )
        )
