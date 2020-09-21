import abc
import dataclasses
import re
import typing

from airq.config import db
from airq.models.clients import Client
from airq.models.clients import ClientIdentifierType
from airq.models.events import Event
from airq.models.events import EventType


class CommandHandlerProtocol(typing.Protocol):
    def handle(self, **kwargs: typing.Any) -> typing.List[str]:
        ...


class CommandHandlerFactoryProtocol(typing.Protocol):
    def __call__(
        self, client: Client, user_input: str, **kwargs: typing.Any
    ) -> CommandHandlerProtocol:
        ...


@dataclasses.dataclass
class Route:
    """Routes commands matching the given pattern to the given handler.

    This is used to create declarative mappings from command handlers to user 
    input (i.e., commands), and should not be instantiated directly: rather, 
    use ``ApiCommandHandler.route()`` to create an association between a
    handler and a command. As an example::

        ROUTES = [
            GetQualityHandler.route(
                pattern=r"^d$", mode=GetQualityHandler.Mode.DETAILS
            )
        ]

    This will cause the command "d" to be handled by the ``GetQualityHandler``,
    which will be instantiated with mode set to 
    ``GetQualityHandler.Mode.DETAILS``.

    """

    pattern: str
    factory: CommandHandlerFactoryProtocol
    extra: typing.Dict[str, typing.Any]

    def match(self, user_input: str) -> typing.Optional[re.Match]:
        return re.match(self.pattern, user_input, re.IGNORECASE)

    def handle(
        self, client: Client, user_input: str, **kwargs: typing.Any
    ) -> typing.List[str]:
        cmd = self.factory(client, user_input, **self.extra)
        return cmd.handle(**kwargs)


class ApiCommandHandler(abc.ABC):
    def __init__(self, client: Client, user_input: str):
        self.client = client
        self.user_input = user_input

    @classmethod
    def route(cls, pattern: str, **extra: typing.Any):
        """Route a command to this handler.

        The command to be routed is given by ``pattern``, and the command
        handler will be instantiated with the keyword arguments given in
        ``extra``, as well as with the default ``client`` and ``user_input``
        parameters.

        :param pattern: The pattern to route to this handler.

        :param extra: Additional keyword arguments to use when instantiating
            the handler.

        """
        return Route(pattern=pattern, factory=cls, extra=extra)

    @abc.abstractmethod
    def handle(self) -> typing.List[str]:
        ...

    def _record_event(self, type_code: EventType, **data: typing.Any) -> Event:
        return Event.query.create(self.client.id, type_code, **data)
