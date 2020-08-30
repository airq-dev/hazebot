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

from airq import metrics
from airq.cache import cache


app = Flask(__name__)
config = {"CACHE_TYPE": "simple", "CACHE_DEFAULT_TIMEOUT": 300}
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
    if len(parts) == 2:
        body, provider_type = parts
    else:
        provider_type = ""
    resp.message(metrics.get_message_for_zipcode(body, provider_type))
    return str(resp)


@app.route("/quality", methods=["GET"])
def quality() -> str:
    zipcode = request.args.get("zipcode", "").strip()
    provider_type = request.args.get("provider", "").strip()
    return metrics.get_message_for_zipcode(zipcode, provider_type, separator="<br>")
