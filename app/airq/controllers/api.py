from flask import g
from flask import request

from airq import commands
from airq.commands.base import MessageResponse
from airq.config import csrf
from airq.lib.client_preferences import ClientPreferencesRegistry, InvalidPrefValue
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
    response = commands.handle_command(
        zipcode, phone_number, ClientIdentifierType.PHONE_NUMBER, supported_locale
    )
    return response.serialize()


def test_command(locale: str) -> str:
    supported_locale = _get_supported_locale(locale)
    g.locale = supported_locale

    if request.headers.getlist("X-Forwarded-For"):
        ip = request.headers.getlist("X-Forwarded-For")[0]
    else:
        ip = request.remote_addr

    args = request.args.copy()
    command = args.pop("command", "").strip()
    overrides = {}
    for k, v in args.items():
        pref = ClientPreferencesRegistry.get_by_name(k)
        if pref:
            try:
                overrides[pref] = pref.validate(v)
            except InvalidPrefValue as e:
                msg = str(e)
                if not msg:
                    msg = '{}: Invalid value "{}"'.format(pref.name, v)
                return MessageResponse().write(msg).as_html()

    with ClientPreferencesRegistry.register_overrides(overrides):
        response = commands.handle_command(
            command, ip, ClientIdentifierType.IP, supported_locale
        )

    return response.as_html()
