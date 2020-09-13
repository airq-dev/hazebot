from flask import request
from twilio.twiml.messaging_response import MessagingResponse

from airq import commands
from airq.models.clients import ClientIdentifierType


def healthcheck() -> str:
    return "OK"


def sms_reply() -> str:
    resp = MessagingResponse()
    zipcode = request.values.get("Body", "").strip()
    phone_number = request.values.get("From", "").strip()
    message = commands.handle_command(
        zipcode, phone_number, ClientIdentifierType.PHONE_NUMBER
    )
    resp.message(message)
    return str(resp)


def quality() -> str:
    zipcode = request.args.get("zipcode", "").strip()
    if request.headers.getlist("X-Forwarded-For"):
        ip = request.headers.getlist("X-Forwarded-For")[0]
    else:
        ip = request.remote_addr
    return commands.handle_command(zipcode, ip, ClientIdentifierType.IP)
