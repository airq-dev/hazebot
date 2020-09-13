import typing

from airq.commands.base import ApiCommandHandler


class InvalidInputHandler(ApiCommandHandler):
    def handle(self) -> typing.List[str]:
        message = [
            f'Unrecognized option "{self.user_input}". Reply with your zipcode for air quality information.',
            "",
        ]
        message.extend(self._get_menu())
        return message
