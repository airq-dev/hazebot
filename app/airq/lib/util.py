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


def data_matches_schema(
    data: typing.Dict[str, typing.Any], obj: typing.Type[object]
) -> bool:
    annotations = typing.get_type_hints(obj)
    for variable, expected_type in annotations.items():
        datum = data.get(variable)
        if datum is None:
            continue
        if not _data_matches_schema_inner(datum, expected_type):
            return False
    return True


def _data_matches_schema_inner(
    data: typing.Any, expected_type: typing.Type[object]
) -> bool:
    if expected_type is typing.Any:
        return True
    if isinstance(expected_type, typing._GenericAlias):  # type: ignore
        typ = expected_type.__origin__
        if not isinstance(data, typ):
            return False
        args = expected_type.__args__
        if typ is list:
            for v in data:
                if not _data_matches_schema_inner(v, args[0]):
                    return False
        else:
            raise TypeError(f"{typ} is unsupported")
    elif not isinstance(data, expected_type):
        return False
    return True
