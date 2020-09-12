from flask import request
from twilio.twiml.messaging_response import MessagingResponse

from airq.lib.readings import pm25_to_aqi
from airq.air_quality import get_metrics_for_zipcode
from airq.models.requests import ClientIdentifierType, insert_request


def healthcheck() -> str:
    return "OK"


def sms_reply() -> str:
    resp = MessagingResponse()
    zipcode = request.values.get("Body", "").strip()
    phone_number = request.values.get("From", "").strip()
    resp.message(_get_message_for_zipcode(zipcode))
    insert_request(zipcode, phone_number, ClientIdentifierType.PHONE_NUMBER)
    return str(resp)


def quality() -> str:
    zipcode = request.args.get("zipcode", "").strip()
    message = _get_message_for_zipcode(zipcode, separator="<br>")
    if request.headers.getlist("X-Forwarded-For"):
        ip = request.headers.getlist("X-Forwarded-For")[0]
    else:
        ip = request.remote_addr
    insert_request(zipcode, ip, ClientIdentifierType.IP)
    return message


def _get_message_for_zipcode(target_zipcode: str, separator: str = "\n") -> str:
    metrics = get_metrics_for_zipcode(target_zipcode)
    target_metrics = metrics.get(target_zipcode)
    if not target_metrics:
        return f'Oops! We couldn\'t determine the air quality for "{target_zipcode}". Please try a different zip code.'
    else:
        message = f"Air quality near {target_metrics.city_name} {target_zipcode} is {target_metrics.pm25_level.display.upper()}"
        aqi = pm25_to_aqi(target_metrics.average_pm25)
        if aqi:
            message += f" (AQI: {aqi})"
        message += "."

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
            message += separator
            message += separator
            message += "Try these other places near you for better air quality:"
            for m in lower_pm25_metrics:
                message += separator
                # TODO: add city when availible
                message += " - {} {}: {}".format(
                    m.city_name, m.zipcode, m.pm25_level.display
                )

        message += separator
        message += separator
        message += f"Average PM2.5 from {target_metrics.num_readings} sensor(s) near {target_zipcode} is {target_metrics.average_pm25} µg/m³."
        return message
