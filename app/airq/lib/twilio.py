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


def send_sms(body: str, to_number: str, locale: str):
    from_number = config.TWILIO_NUMBERS.get(locale)
    if not from_number:
        logger.exception("Couldn't find a Twilio number for %s", locale)
        return

    if config.DEV:
        logger.info("Would send SMS to %s from %s: %s", to_number, from_number, body)
    else:
        client = Client(config.TWILIO_SID, config.TWILIO_AUTHTOKEN)
        client.messages.create(body=body, to=to_number, from_=from_number)
