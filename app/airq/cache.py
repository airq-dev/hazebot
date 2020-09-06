import typing

import flask
import flask_caching
from flask_caching.backends import SimpleCache


TKey = typing.TypeVar("TKey")
TVal = typing.TypeVar("TVal")
TFallback = typing.TypeVar("TFallback")


REMOTE_CACHE = flask_caching.Cache()


# A cache which should be used to cache stuff in memory, not in memcached.
LOCAL_CACHE = SimpleCache()


def init(app: flask.Flask):
    REMOTE_CACHE.init_app(app)


class Cache(typing.Generic[TKey, TVal]):
    def __init__(
        self,
        *,
        prefix: str,
        timeout: int,
        use_remote: bool = True,
        use_local: bool = True,
    ):
        if not use_local and not use_remote:
            raise RuntimeError(
                "You must set one or more of `use_remote` or `use_local` to True."
            )
        self._prefix = prefix
        self._timeout = timeout
        self._use_remote = use_remote
        self._use_local = use_local

    def _make_key(self, key: TKey) -> str:
        return f"{self._prefix}{key}"

    @typing.overload
    def get(self, key: TKey) -> typing.Optional[TVal]:
        ...

    @typing.overload
    def get(self, key: TKey, default: TFallback) -> typing.Union[TVal, TFallback]:
        ...

    def get(self, key, default=None):
        key = self._make_key(key)
        res = None
        if self._use_local:
            res = LOCAL_CACHE.get(key)
        if res is None and self._use_remote:
            res = REMOTE_CACHE.get(key)
        if res is None:
            return default
        return res

    def get_many(self, keys: typing.Iterable[TKey]) -> typing.Dict[TKey, TVal]:
        if not keys:
            return {}
        mapped = {k: self._make_key(k) for k in keys}
        results = {}
        if self._use_local:
            values = LOCAL_CACHE.get_many(*mapped.values())
            for k, v in zip(list(mapped), values):
                if v is not None:
                    results[k] = v
                    del mapped[k]
        if keys and self._use_remote:
            values = REMOTE_CACHE.get_many(*mapped.values())
            for k, v in zip(mapped, values):
                if v is not None:
                    results[k] = v
        return results

    def set(self, key: TKey, value: TVal):
        k = self._make_key(key)
        if self._use_local:
            LOCAL_CACHE.set(k, value, self._timeout)
        if self._use_remote:
            REMOTE_CACHE.set(k, value, self._timeout)

    def set_many(self, mapping: typing.Dict[TKey, TVal]):
        if not mapping:
            return
        m = {self._make_key(key): value for key, value in mapping.items()}
        if self._use_local:
            LOCAL_CACHE.set_many(m, timeout=self._timeout)
        if self._use_remote:
            REMOTE_CACHE.set_many(m, timeout=self._timeout)


def memoize(*, timeout: int, use_local=True, use_remote=True):
    if not use_local and not use_remote:
        raise RuntimeError(
            "You must set one or more of `use_remote` or `use_local` to True."
        )

    def _make_key(args, kwargs):
        return "".join(map(str, args)) + str(sorted(kwargs.items()))

    def decorator(func):
        def wrapper(*args, **kwargs):
            key = _make_key(args, kwargs)
            if use_local:
                res = LOCAL_CACHE.get(key)
            if res is None and use_remote:
                res = REMOTE_CACHE.get(key)
            if res is None:
                res = func(*args, **kwargs)
                if use_local:
                    LOCAL_CACHE.set(key, res)
                if use_remote:
                    REMOTE_CACHE.set(key, res)

            return res

        return wrapper

    return decorator
