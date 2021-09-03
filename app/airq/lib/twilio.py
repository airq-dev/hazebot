import abc
import dataclasses
import enum
import logging
import typing

from airq import config

from twilio.base.exceptions import TwilioRestException
from twilio.rest import Client


logger = logging.getLogger(__name__)


class TwilioErrorCode(enum.IntEnum):
    OUT_OF_REGION = 21408
    UNSUBSCRIBED = 21610

    @classmethod
    def from_exc(cls, exc: TwilioRestException) -> typing.Optional["TwilioErrorCode"]:
        for m in cls:
            if m.value == exc.code:
                return m
        return None


def send_sms(
    body: str, to_number: str, locale: str, media: typing.Optional[str] = None
):
    from_number = config.TWILIO_NUMBERS.get(locale)
    if not from_number:
        logger.exception("Couldn't find a Twilio number for %s", locale)
        return

    message = TwilioMessage(body=body, to=to_number, from_=from_number, media_url=media)
    TwilioClient.get_instance().send(message)


@dataclasses.dataclass
class TwilioMessage:
    body: str
    to: str
    from_: str
    media_url: typing.Optional[str]

    def as_dict(self) -> typing.Dict[str, str]:
        out = dict(body=self.body, to=self.to, from_=self.from_)
        if self.media_url is not None:
            out["media_url"] = self.media_url
        return out

    def is_match(
        self,
        body: typing.Optional[str],
        to: typing.Optional[str],
        from_: typing.Optional[str],
        media_url: typing.Optional[str],
    ) -> bool:
        if body is not None:
            if self.body != body:
                return False
        if to is not None:
            if self.to != to:
                return False
        if from_ is not None:
            if self.from_ != from_:
                return False
        if media_url is not None:
            if self.media_url != media_url:
                return False
        return True


class TwilioClient(abc.ABC):
    _instance: typing.Optional["TwilioClient"] = None

    @classmethod
    def get_instance(cls) -> "TwilioClient":
        if cls._instance is None:
            cls._instance = cls._get_client_for_env()
        return cls._instance

    @staticmethod
    def _get_client_for_env() -> "TwilioClient":
        if config.TESTING:
            return TwilioTestClient()
        elif config.DEV:
            return TwilioDevClient()
        else:
            return TwilioProdClient()

    @abc.abstractmethod
    def send(self, message: TwilioMessage) -> None:
        ...


class TwilioProdClient(TwilioClient):
    def __init__(self) -> None:
        self.client = Client(config.TWILIO_SID, config.TWILIO_AUTHTOKEN)

    def send(self, message: TwilioMessage) -> None:
        self.client.messages.create(**message.as_dict())


class TwilioDevClient(TwilioClient):
    def send(self, message: TwilioMessage) -> None:
        logger.info("Would send SMS: %s", message.as_dict())


# TODO: This should maybe live somewhere else
class TwilioTestClient(TwilioClient):
    def send(self, message: TwilioMessage) -> None:
        self.messages.append(message)

    messages: typing.List[TwilioMessage] = []

    @classmethod
    def reset(cls):
        cls.messages = []

    @classmethod
    def has_message(
        cls,
        *,
        body: typing.Optional[str] = None,
        to: typing.Optional[str] = None,
        from_: typing.Optional[str] = None,
        media_url: typing.Optional[str] = None
    ) -> bool:
        return any(
            message.is_match(body, to, from_, media_url) for message in cls.messages
        )

    @classmethod
    def has_last_message(
        cls,
        *,
        body: typing.Optional[str] = None,
        to: typing.Optional[str] = None,
        from_: typing.Optional[str] = None,
        media_url: typing.Optional[str] = None
    ) -> bool:
        return bool(cls.messages) and cls.messages[-1].is_match(
            body, to, from_, media_url
        )
