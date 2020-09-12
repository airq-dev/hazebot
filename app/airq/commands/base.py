import abc
import dataclasses
import typing

from airq.models.requests import ClientIdentifierType


@dataclasses.dataclass
class CommandContext:
    identifier: str
    identifier_type: ClientIdentifierType
    user_input: str


class CommandMeta(abc.ABCMeta):
    def parse(self, ctx: CommandContext) -> typing.Optional["ApiCommand"]:
        ...


class ApiCommand(metaclass=CommandMeta):
    ctx: CommandContext

    def __init__(self, ctx: CommandContext):
        self.ctx = ctx

    @classmethod
    @abc.abstractmethod
    def parse(cls, ctx: CommandContext) -> typing.Optional["ApiCommand"]:
        ...

    @abc.abstractmethod
    def handle(self) -> typing.List[str]:
        ...

    def _get_menu(self) -> typing.List[str]:
        return [
            "<zipcode> - aqi for the zipcode",
            "r - aqi for the last zipcode you checked",
            "d <zipcode> - aqi details for the zipcode",
            "m - display this menu",
        ]