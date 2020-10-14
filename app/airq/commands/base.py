import abc
import html
import re
import typing

from flask_babel import gettext
from twilio.twiml import messaging_response

from airq.models.clients import Client


class MessageResponse:
    def __init__(self, body: str = "", media: typing.Optional[str] = None):
        self._body = body
        self._media = media

    @classmethod
    def from_strings(
        cls, strings: typing.List[str], media: typing.Optional[str] = None
    ) -> "MessageResponse":
        return cls(body="\n".join(strings), media=media)

    def __str__(self) -> str:
        return self.serialize()

    def serialize(self) -> str:
        response = messaging_response.MessagingResponse()
        message = messaging_response.Message()
        message.body(self._body)
        if self._media:
            message.media(self._media)
        response.append(message)
        return str(response)

    @property
    def body(self) -> str:
        return self._body

    def as_html(self) -> str:
        return html.escape(self._body).replace("\n", "<br>")

    def write(self, content: str, sep: str = "\n"):
        if self._body:
            self._body += sep
        self._body += content

    def media(self, media: str):
        self._media = media


class SMSCommand(abc.ABC):
    def __init__(self, client: Client, user_input: str):
        self.client = client
        self.user_input = user_input

    @abc.abstractmethod
    def should_handle(self) -> bool:
        ...

    @abc.abstractmethod
    def handle(self) -> MessageResponse:
        ...

    def _get_missing_zipcode_message(self) -> MessageResponse:
        return MessageResponse(
            body=gettext(
                "Looks like you haven't use hazebot before! Please text us a zipcode and we'll send you the air quality."
            )
        )


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
