import html
import typing

from flask import request
from twilio.twiml.messaging_response import MessagingResponse

from airq.lib.readings import pm25_to_aqi
from airq.air_quality import get_metrics_for_zipcode
from airq.models.requests import ClientIdentifierType, get_last_zipcode, insert_request


def healthcheck() -> str:
    return "OK"


def sms_reply() -> str:
    resp = MessagingResponse()
    zipcode = request.values.get("Body", "").strip()
    phone_number = request.values.get("From", "").strip()
    message = _handle_command(zipcode, phone_number, ClientIdentifierType.PHONE_NUMBER)
    resp.message(message)
    return str(resp)


def quality() -> str:
    zipcode = request.args.get("zipcode", "").strip()
    if request.headers.getlist("X-Forwarded-For"):
        ip = request.headers.getlist("X-Forwarded-For")[0]
    else:
        ip = request.remote_addr
    return _handle_command(zipcode, ip, ClientIdentifierType.IP)


def _handle_command(
    command: str, identifier: str, identifier_type: ClientIdentifierType
) -> str:
    parts = command.split()
    directive = command[0]
    details = False
    message = []

    if len(parts) < 3:
        zipcode = None
        if len(parts) == 2:
            if directive == "d":
                details = True
                zipcode = parts[1]
        elif directive == "m":
            message = _get_menu()
        elif directive == "r":
            zipcode = get_last_zipcode(identifier, identifier_type)
        else:
            zipcode = command

        if zipcode:
            message = _get_message_for_zipcode(zipcode, details=details)
            if message:
                insert_request(zipcode, identifier, identifier_type)
            else:
                message = [
                    f'Oops! We couldn\'t determine the air quality for "{zipcode}". Please try a different zip code.'
                ]

    if not message:
        message = ['Unrecognized option "{command}". Try one of these: ']
        message.extend(_get_menu())

    if identifier_type == ClientIdentifierType.IP:
        message = [html.escape(m) for m in message]
        separator = "<br>"
    else:
        separator = "\n"

    return separator.join(message)


def _get_message_for_zipcode(
    target_zipcode: str, details: bool = False
) -> typing.List[str]:
    metrics = get_metrics_for_zipcode(target_zipcode, details=details)
    target_metrics = metrics.get(target_zipcode)
    if not target_metrics:
        return []

    message = []
    aqi = pm25_to_aqi(target_metrics.average_pm25)
    message.append(
        "Air quality near {} {} is {}{}.".format(
            target_metrics.city_name,
            target_zipcode,
            target_metrics.pm25_level.display.upper(),
            f" (AQI: {aqi})" if aqi else "",
        )
    )

    if details:
        num_desired = 3
        lower_pm25_metrics = sorted(
            [
                m
                for m in metrics.values()
                if m.zipcode != target_zipcode
                and m.pm25_level < target_metrics.pm25_level
            ],
            # Sort by pm25 level, and then by distance from the desired zip to break ties
            key=lambda m: (m.pm25_level, m.distance),
        )[:num_desired]
        if lower_pm25_metrics:
            message.append("")
            message.append("Try these other places near you for better air quality:")
            for m in lower_pm25_metrics:
                message.append(
                    " - {} {}: {}".format(m.city_name, m.zipcode, m.pm25_level.display)
                )

        message.append("")
        message.append(
            f"Average PM2.5 from {target_metrics.num_readings} sensor(s) near {target_zipcode} is {target_metrics.average_pm25} µg/m³."
        )

    message.append("")
    message.append('Respond with "m" to get a full list of commands.')

    return message


def _get_menu() -> typing.List[str]:
    return [
        "<zipcode> - aqi for the zipcode",
        "r - aqi for the last zipcode you checked",
        "d <zipcode> - aqi details for the zipcode",
        "m - display this menu",
    ]
