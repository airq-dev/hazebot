import gc
import itertools
import typing


T = typing.TypeVar("T")


def chunk_list(
    iterable: typing.Iterable[T], batch_size: int = 1000
) -> typing.Iterator[typing.List[T]]:
    it = iter(iterable)
    while True:
        chunk = list(itertools.islice(it, batch_size))
        if not chunk:
            return
        yield chunk
        gc.collect()
