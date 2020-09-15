import typing

from airq.commands.base import ApiCommandHandler


class InvalidInputHandler(ApiCommandHandler):
    def handle(self) -> typing.List[str]:
        return [
            'Unrecognized option "{}". Reply with M for the menu{}.'.format(
                self.user_input,
                " or S to stop this alert" if self.client.get_subscription() else "",
            )
        ]
