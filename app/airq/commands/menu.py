import typing

from airq.commands.base import ApiCommandHandler


class ShowMenuHandler(ApiCommandHandler):
    def handle(self) -> typing.List[str]:
        return self._get_menu()
