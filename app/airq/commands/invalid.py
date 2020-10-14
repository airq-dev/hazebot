from flask_babel import gettext

from airq.commands.base import MessageResponse
from airq.commands.base import SMSCommand


class InvalidInput(SMSCommand):
    def should_handle(self) -> bool:
        return True

    def handle(self) -> MessageResponse:
        message = gettext(
            'Unrecognized option "%(user_input)s". ', user_input=self.user_input
        )
        if self.client.is_enabled_for_alerts:
            message += gettext("Reply with M for the menu or U to stop this alert.")
        else:
            message += gettext("Reply with M for the menu.")
        return MessageResponse(body=message)
