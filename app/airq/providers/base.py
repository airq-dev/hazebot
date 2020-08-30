import abc
import collections
import dataclasses
import enum
import logging
import typing


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


class IProvider(abc.ABC):
    @abc.abstractmethod
    def get_metrics(self, zipcode: str) -> typing.Optional[Metrics]:
        pass


class Provider(IProvider):
    TYPE: ProviderType

    def __init__(self):
        self._logger = logging.getLogger(f"airq.providers.{self.TYPE}")

    def _generate_metrics(self, metrics: TMetrics, zipcode: str) -> Metrics:
        return Metrics(metrics, zipcode, self.TYPE)

    @property
    def logger(self) -> logging.Logger:
        return self._logger
