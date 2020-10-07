import abc
import re
import typing

from flask_babel import gettext

from airq.models.clients import Client


class SMSCommand(abc.ABC):
    def __init__(self, client: Client, user_input: str):
        self.client = client
        self.user_input = user_input

    @abc.abstractmethod
    def should_handle(self) -> bool:
        ...

    @abc.abstractmethod
    def handle(self) -> typing.List[str]:
        ...

    def _get_missing_zipcode_message(self) -> typing.List[str]:
        return [
            gettext(
                "Looks like you haven't use hazebot before! Please text us a zipcode and we'll send you the air quality."
            )
        ]


class RegexCommand(SMSCommand):
    def __init__(self, client: Client, user_input: str):
        super().__init__(client, user_input)
        self.match = re.match(self.pattern, self.user_input, re.IGNORECASE)
        if self.match:
            self.params = self.match.groupdict()
        else:
            self.params = {}

    @property
    @abc.abstractmethod
    def pattern(self) -> str:
        ...

    def should_handle(self) -> bool:
        return bool(self.match)
