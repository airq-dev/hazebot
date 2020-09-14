import logging

from airq import config

from twilio.rest import Client


logger = logging.getLogger(__name__)


def send_sms(body: str, phone_number: str):
    if config.DEBUG:
        logger.info("Would send SMS to %s: %s", phone_number, body)
    else:
        client = Client(config.TWILIO_SID, config.TWILIO_AUTHTOKEN)
        client.messages.create(body=body, to=phone_number, from_=config.TWILIO_NUMBER)
