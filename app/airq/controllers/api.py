from flask import g
from flask import request

from airq import commands
from airq.config import csrf
from airq.models.clients import ClientIdentifierType


SUPPORTED_LANGUAGES = ["en", "es"]


def healthcheck() -> str:
    return "OK"


def _get_supported_locale(locale: str) -> str:
    if locale in SUPPORTED_LANGUAGES:
        return locale
    return "en"


@csrf.exempt
def sms_reply(locale: str) -> str:
    supported_locale = _get_supported_locale(locale)
    g.locale = supported_locale

    zipcode = request.values.get("Body", "").strip()

    phone_number = request.values.get("From", "").strip()
    if phone_number.startswith("whatsapp:"):
        phone_number = phone_number.lstrip("whatsapp:")
        identifier_type = ClientIdentifierType.WHATSAPP
    else:
        identifier_type = ClientIdentifierType.PHONE_NUMBER

    response = commands.handle_command(
        zipcode, phone_number, identifier_type, supported_locale
    )

    return response.serialize()


def test_command(locale: str) -> str:
    supported_locale = _get_supported_locale(locale)
    g.locale = supported_locale

    command = request.args.get("command", "").strip()

    if request.headers.getlist("X-Forwarded-For"):
        ip = request.headers.getlist("X-Forwarded-For")[0]
    else:
        ip = request.remote_addr

    response = commands.handle_command(
        command, ip, ClientIdentifierType.IP, supported_locale
    )

    return response.as_html()
