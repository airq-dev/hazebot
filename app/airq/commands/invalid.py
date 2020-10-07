import typing

from flask_babel import gettext

from airq.commands.base import SMSCommand


class InvalidInput(SMSCommand):
    def should_handle(self) -> bool:
        return True

    def handle(self) -> typing.List[str]:
        return [
            gettext(
                'Unrecognized option "%(user_input)s". Reply with M for the menu%(alert_message)s.',
                user_input=self.user_input,
                alert_message=" or U to stop this alert" if self.client.is_enabled_for_alerts else "",
            )
        ]
