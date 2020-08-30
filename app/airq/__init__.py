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
from flask_caching import Cache
from twilio.twiml.messaging_response import MessagingResponse
from airq.providers import get_providers
from airq.providers.base import Metrics, Provider


config = {"CACHE_TYPE": "simple", "CACHE_DEFAULT_TIMEOUT": 300}


app = Flask(__name__)
app.config.from_mapping(config)
cache = Cache(app)


@app.route("/", methods=["GET"])
def healthcheck() -> str:
    return "OK"


@app.route("/sms", methods=["POST"])
def sms_reply() -> str:
    resp = MessagingResponse()
    body = request.values.get("Body", "").strip()
    parts = body.split(" ")
    if len(parts) == 2:
        body, provider_type = parts
    else:
        provider_type = ""
    resp.message(_get_metrics_message_for_zipcode(body, provider_type))
    return str(resp)


@app.route("/quality", methods=["GET"])
def quality() -> str:
    zipcode = request.args.get("zipcode", "").strip()
    provider_type = request.args.get("provider", "").strip()
    return _get_metrics_message_for_zipcode(zipcode, provider_type, separator="<br>")

#
# Metrics
#
# TODO: Make this its own module and figure out caching depedencies
#

def _get_metrics_message_for_zipcode(
    zipcode: str, provider_type: str, separator: str = "\n"
) -> str:
    if zipcode.isdigit() and len(zipcode) == 5:
        providers = get_providers([provider_type])
        metrics = _aggregate_metrics(zipcode, providers)
        if metrics:
            return _format_metrics(zipcode, metrics, separator)

    return f'Oops! We couldn\'t determine the air quality for "{zipcode}". Please try a different zip code.'


def _aggregate_metrics(
    zipcode: str, providers: typing.List[Provider]
) -> typing.List[Metrics]:
    all_metrics = []
    for provider in providers:
        metrics = _get_metrics(zipcode, provider)
        if metrics:
            all_metrics.append(metrics)
    return all_metrics


@cache.memoize(timeout=60 * 60)
def _get_metrics(zipcode: str, provider: Provider) -> typing.Optional[Metrics]:
    return provider.get_metrics(zipcode)


def _format_metrics(
    zipcode: str, all_metrics: typing.List[Metrics], separator: str
) -> str:
    lines = [f"Air Quality Metrics Near {zipcode}"]
    for metrics in all_metrics:
        lines.append("")
        lines.extend("{}: {}".format(m.name, m.value) for m in metrics)
        lines.append(f"(Provider: {metrics.provider})")
    return separator.join(lines)
