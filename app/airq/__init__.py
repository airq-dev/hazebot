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

from airq.cache import cache
from airq.purpleair import PURPLEAIR_PROVIDER


app = Flask(__name__)
config = {
    "CACHE_TYPE": "memcached",
    "CACHE_DEFAULT_TIMEOUT": 300,
    "CACHE_MEMCACHED_SERVERS": (os.getenv("MEMCACHED_SERVER"),),
}
app.config.from_mapping(config)
cache.init_app(app)


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


def _get_message_for_zipcode(zipcode: str, separator: str = "\n") -> str:
    if zipcode.isdigit() and len(zipcode) == 5:
        metrics = PURPLEAIR_PROVIDER.get_metrics(zipcode)
        if metrics:
            return separator.join(
                [
                    f"Air quality near {zipcode}:",
                    metrics.pm25_display.upper(),
                    f"Average pm2.5: {metrics.pm25}",
                    "All readngs: {}".format(", ".join(map(str, metrics.readings))),
                    "(max distance: {})".format(metrics.max_sensor_distance,),
                ]
            )

    return f'Oops! We couldn\'t determine the air quality for "{zipcode}". Please try a different zip code.'
