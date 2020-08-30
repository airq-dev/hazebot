import logging
import typing

from airq.cache import cache
from airq.providers import get_providers
from airq.providers.base import Metrics, Provider, ProviderOutOfService


logger = logging.getLogger(__name__)


def get_message_for_zipcode(
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
        try:
            metrics = provider.get_metrics_cached(zipcode)
        except ProviderOutOfService as e:
            logger.exception(
                '%s unable to provide metrics for %s: %s', provider, zipcode, e
            )
        else:
            if metrics:
                all_metrics.append(metrics)
    return all_metrics


def _format_metrics(
    zipcode: str, all_metrics: typing.List[Metrics], separator: str
) -> str:
    lines = [f"Air Quality Metrics Near {zipcode}"]
    for metrics in all_metrics:
        lines.append("")
        lines.extend("{}: {}".format(m.name, m.value) for m in metrics)
        lines.append(f"(Provider: {metrics.provider})")
    return separator.join(lines)
