import typing

from airq.commands.base import ApiCommandHandler


class InvalidInputHandler(ApiCommandHandler):
    def handle(self) -> typing.List[str]:
        return [
            'Unrecognized option "{}". Reply with M for the menu{}.'.format(
                self.user_input,
                " or U to stop this alert" if self.client.is_enabled_for_alerts else "",
            )
        ]
