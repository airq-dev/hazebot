import typing

import flask
import flask_caching


TKey = typing.TypeVar("TKey")
TVal = typing.TypeVar("TVal")
TFallback = typing.TypeVar("TFallback")


_ROOT_CACHE = flask_caching.Cache()


def init(app: flask.Flask):
    _ROOT_CACHE.init_app(app)


class Cache(typing.Generic[TKey, TVal]):
    def __init__(self, *, prefix: str, timeout: int):
        self._prefix = prefix
        self._timeout = timeout

    def _make_key(self, key: TKey) -> str:
        return f"{self._prefix}{key}"

    @typing.overload
    def get(self, key: TKey) -> typing.Optional[TVal]:
        ...

    @typing.overload
    def get(self, key: TKey, default: TFallback) -> typing.Union[TVal, TFallback]:
        ...

    def get(self, key, default=None):
        res = _ROOT_CACHE.get(self._make_key(key))
        if res is None:
            return default
        return res

    def get_many(self, keys: typing.Iterable[TKey]) -> typing.Dict[TKey, TVal]:
        values = _ROOT_CACHE.get_many(*[self._make_key(key) for key in keys])
        return {k: v for k, v in zip(keys, values) if v is not None}

    def set(self, key: TKey, value: TVal):
        _ROOT_CACHE.set(self._make_key(key), value, self._timeout)

    def set_many(self, mapping: typing.Dict[TKey, TVal]):
        _ROOT_CACHE.set_many(
            {self._make_key(key): value for key, value in mapping.items()},
            timeout=self._timeout,
        )


DEAD: Cache[int, bool] = Cache(
    prefix="purpleair-pm25-sensor-dead-", timeout=60 * 60
)


DISTANCE: Cache[str, typing.Dict[int, float]] = Cache(
    prefix="purpleair-sensor-distance", timeout=24 * 60 * 60
)


PM25: Cache[int, float] = Cache(
    prefix="purpleair-pm25-sensor-reading-", timeout=60 * 10
)
