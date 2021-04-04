import abc
import enum
import typing


T = typing.TypeVar("T", bound="ChoicesEnum")


class ChoicesEnum(enum.Enum):
    @property
    @abc.abstractmethod
    def display(self) -> str:
        ...

    @classmethod
    def from_value(cls: typing.Type[T], value: typing.Any) -> T:
        return cls(value)


class IntChoicesEnum(int, ChoicesEnum):
    pass


class StrChoicesEnum(str, ChoicesEnum):
    pass
