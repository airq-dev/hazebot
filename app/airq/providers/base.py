import abc
import collections
import dataclasses
import enum
import logging
import typing

from airq.cache import cache


@enum.unique
class ProviderType(str, enum.Enum):
    AIRNOW = "airnow"
    PURPLEAIR = "purpleair"


TMeasurement = typing.Union[str, int, float]


TMetrics = typing.List[typing.Tuple[str, TMeasurement]]


class Metric(typing.NamedTuple):
    name: str
    value: TMeasurement


class Metrics:
    def __init__(self, metrics: TMetrics, zipcode: str, provider: ProviderType):
        self._metrics = [Metric(k, v) for k, v in metrics]
        self._provider = provider
        self._zipcode = zipcode

    def __repr__(self) -> str:
        return f"Metrics({self._metrics}, {self._zipcode}, {self._provider})"

    def __bool__(self) -> bool:
        return bool(self._metrics)

    def __eq__(self, other: typing.Any) -> bool:
        return (
            isinstance(other, Metrics)
            and self._metrics == other.metrics
            and self._zipcode == other.zipcode
            and self._provider == other.provider
        )

    def __iter__(self) -> typing.Iterator[Metric]:
        return iter(self._metrics)

    @property
    def metrics(self) -> typing.List[Metric]:
        return self._metrics

    @property
    def provider(self) -> ProviderType:
        return self._provider

    @property
    def zipcode(self) -> str:
        return self._zipcode


class ProviderOutOfService(Exception):
    pass


class Provider(abc.ABC):
    TYPE: ProviderType

    def __init__(self):
        self._logger = logging.getLogger(self._get_identifier())

    def __repr__(self):
        return f"{self.__class__.__name__}()"

    def _generate_metrics(self, metrics: TMetrics, zipcode: str) -> Metrics:
        return Metrics(metrics, zipcode, self.TYPE)

    def _get_identifier(self, prefix: str = "") -> str:
        return f"{prefix}airq.providers.{self.TYPE}"

    # @cache.memoize(timeout=60 * 60)
    def get_metrics_cached(self, zipcode: str) -> typing.Optional[Metrics]:
        return self.get_metrics(zipcode)

    @abc.abstractmethod
    def get_metrics(self, zipcode: str) -> typing.Optional[Metrics]:
        pass

    @property
    def logger(self) -> logging.Logger:
        return self._logger

    @property
    def is_out_of_service(self) -> bool:
        key = self._get_identifier("down-")
        return bool(cache.get(key))

    def mark_out_of_service(
        self,
        timeout: int = (
            60 * 2
        ),  # Default timeout of 2 minutes in case the problem is rate-limiting
    ):
        key = self._get_identifier("down-")
        cache.set(key, True, timeout=timeout)
