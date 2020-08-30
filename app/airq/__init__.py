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
from flask_caching import Cache
from twilio.twiml.messaging_response import MessagingResponse
from airq import providers


config = {"CACHE_TYPE": "simple", "CACHE_DEFAULT_TIMEOUT": 300}


app = Flask(__name__)
app.config.from_mapping(config)
cache = Cache(app)


@app.route("/")
def index():
    return "OK"


@app.route("/sms", methods=["POST"])
def sms_reply():
    resp = MessagingResponse()
    body = request.values.get("Body", "").strip()
    parts = body.split(' ')
    if len(parts) == 2:
        body, provider = parts
    else:
        provider = None
    resp.message(_get_forecast_message_for_zipcode(body, provider))
    return str(resp)


@app.route("/forecast")
def forecast():
    zipcode = request.args.get("zipcode", "").strip()
    provider = request.args.get("provider", "").strip()
    return _get_forecast_message_for_zipcode(zipcode, provider)


@cache.memoize(timeout=60 * 60)
def _get_forecast_message_for_zipcode(zipcode, provider):
    if zipcode.isdigit():
        message = providers.get_message_for_zipcode(zipcode, provider)
        if message:
            return message
    return f'Oops! We couldn\'t determine the air quality for "{zipcode}". Please try a different zip code.'
