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
        metrics = air_quality.get_metrics_for_zipcode(target_zipcode) or {}
    else:
        metrics = {}

    target_metrics = metrics.get(target_zipcode)
    if not target_metrics:
        return f'Oops! We couldn\'t determine the air quality for "{target_zipcode}". Please try a different zip code.'
    else:
        message = separator.join(
            [
                f"Air quality near {target_zipcode}:",
                util.PM25.from_measurement(target_metrics["avg_pm25"]).display.upper(),
                f"Average pm2.5: {target_metrics['avg_pm25']}",
            ]
        )
        if target_metrics["avg_pm25"] >= util.PM25.UNHEALTHY_FOR_SENSITIVE_INDIVIDUALS:
            num_desired = 3
            low_pm25_metrics = []
            good_pm25_metrics = sorted(
                [
                    (zipcode, m["avg_pm25"], m["distance"])
                    for zipcode, m in metrics.items()
                    if zipcode != target_zipcode and m["avg_pm25"] < util.PM25.MODERATE
                ],
                key=lambda t: t[2],
            )
            if good_pm25_metrics:
                low_pm25_metrics += good_pm25_metrics[:num_desired]
                num_desired -= len(low_pm25_metrics)
            if num_desired:
                moderate_pm25_metrics = sorted(
                    [
                        (zipcode, m["avg_pm25"], m["distance"])
                        for zipcode, m in metrics.items()
                        if zipcode != target_zipcode
                        and m["avg_pm25"]
                        < util.PM25.UNHEALTHY_FOR_SENSITIVE_INDIVIDUALS
                    ],
                    key=lambda t: t[2],
                )
                low_pm25_metrics += moderate_pm25_metrics[:num_desired]
            if low_pm25_metrics:
                message += separator
                message += separator
                message += "Here are some nearby locations with better air quality:"
                for zipcode, avg_pm25, distance in low_pm25_metrics:
                    message += separator
                    pm25_display = util.PM25.from_measurement(avg_pm25).display
                    message += f" > {zipcode}: {pm25_display} (average pm2.5: {avg_pm25}) — {distance} from {target_zipcode}"
        else:
            message += separator
            message += "That's not bad!"
        return message
