import typing

from flask_babel import gettext

from airq.commands.base import SMSCommand


class InvalidInput(SMSCommand):
    def should_handle(self) -> bool:
        return True

    def handle(self) -> typing.List[str]:
        return [
            gettext("hello world")
            # gettext('Unrecognized option "{}". Reply with M for the menu{}.').format(
            #     self.user_input,
            #     " or U to stop this alert" if self.client.is_enabled_for_alerts else "",
            # )
        ]
