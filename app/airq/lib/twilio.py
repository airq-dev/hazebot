from airq import config

from twilio.rest import Client


def send_sms(body: str, phone_number: str):
    client = Client(config.TWILIO_SID, config.TWILIO_AUTHTOKEN)
    client.messages.create(body=body, to=phone_number, from_=config.TWILIO_NUMBER)
