import abc
import dataclasses
import typing

from airq.models.clients import Client
from airq.models.clients import ClientIdentifierType


@dataclasses.dataclass
class CommandContext:
    client: Client
    user_input: str


class CommandMeta(abc.ABCMeta):
    def parse(self, ctx: CommandContext) -> typing.Optional["ApiCommand"]:
        ...


class ApiCommand(metaclass=CommandMeta):
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
            "Reply R for safer places, "
            "D for details, "
            "L for previous zip, "
            "and ? for hazebot info."
        ]

    def _get_about(self) -> typing.List[str]:
        return [
            "hazebot runs on PurpleAir sensor data and is a free text service designed to provide accessible local air quality information. Visit hazebot.org to learn more."
        ]
