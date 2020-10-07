import typing

from flask_babel import gettext

from airq.commands.base import SMSCommand


class InvalidInput(SMSCommand):
    def should_handle(self) -> bool:
        return True

    def handle(self) -> typing.List[str]:
        message = gettext(
            'Unrecognized option "%(user_input)s". ', user_input=self.user_input
        )
        if self.client.is_enabled_for_alerts:
            message += gettext("Reply with M for the menu or U to stop this alert.")
        else:
            message += gettext("Reply with M for the menu.")
        return [message]
