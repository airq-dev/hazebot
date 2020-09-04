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

    def set(self, key: TKey, value: TVal):
        _ROOT_CACHE.set(self._make_key(key), value, self._timeout)
