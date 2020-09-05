import os
import typing
from logging.config import dictConfig


# Init logging before doing anything else.
#
# TODO: Send errors to admins as emails
dictConfig(
    {
        "version": 1,
        "formatters": {
            "default": {
                "format": "[%(asctime)s] %(levelname)s in %(module)s: %(message)s",
            }
        },
        "handlers": {
            "wsgi": {
                "class": "logging.StreamHandler",
                "stream": "ext://flask.logging.wsgi_errors_stream",
                "formatter": "default",
            }
        },
        "root": {"level": "INFO", "handlers": ["wsgi"]},
    }
)


from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse

from airq import air_quality
from airq import cache
from airq import middleware
from airq import util


app = Flask(__name__)
app.wsgi_app = middleware.LoggingMiddleware(app.wsgi_app)  # type: ignore
config = {
    "CACHE_TYPE": "memcached",
    "CACHE_DEFAULT_TIMEOUT": 300,
    "CACHE_MEMCACHED_SERVERS": os.getenv("MEMCACHED_SERVERS", "").split(","),
}
app.config.from_mapping(config)
cache.CACHE.init_app(app)


@app.route("/", methods=["GET"])
def healthcheck() -> str:
    return "OK"


@app.route("/sms", methods=["POST"])
def sms_reply() -> str:
    resp = MessagingResponse()
    body = request.values.get("Body", "").strip()
    parts = body.split()
    resp.message(_get_message_for_zipcode(body))
    return str(resp)


@app.route("/quality", methods=["GET"])
def quality() -> str:
    zipcode = request.args.get("zipcode", "").strip()
    return _get_message_for_zipcode(zipcode, separator="<br>")


def _get_message_for_zipcode(target_zipcode: str, separator: str = "\n") -> str:
    if target_zipcode.isdigit() and len(target_zipcode) == 5:
        metrics = air_quality.get_metrics_for_zipcode(target_zipcode)
    else:
        metrics = {}

    target_metrics = metrics.get(target_zipcode)
    if not target_metrics:
        return f'Oops! We couldn\'t determine the air quality for "{target_zipcode}". Please try a different zip code.'
    else:
        message = separator.join(
            [
                f"Air quality near {target_zipcode} is {target_metrics.pm25_level.display.upper()}.",
                "",
                f"PM2.5: {target_metrics.average_pm25} ({target_metrics.num_readings} sensors reporting)",
                f"Min sensor distance: {target_metrics.closest_reading}km",
                f"Max sensor distance: {target_metrics.farthest_reading}km",
                f"All readings: {target_metrics.readings}",
            ]
        )

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
            message += "Here are some nearby locations with better air quality:"
            for m in lower_pm25_metrics:
                message += separator
                message += " > {}: {} (Average PM2.5: {} / {}km from {})".format(
                    m.zipcode,
                    m.pm25_level.display.upper(),
                    m.average_pm25,
                    m.distance,
                    target_zipcode,
                )

        return message
