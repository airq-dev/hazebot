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


def send_sms(body: str, phone_number: str):
    if config.DEBUG:
        logger.info("Would send SMS to %s: %s", phone_number, body)
    else:
        client = Client(config.TWILIO_SID, config.TWILIO_AUTHTOKEN)
        client.messages.create(body=body, to=phone_number, from_=config.TWILIO_NUMBER)
