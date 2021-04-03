import abc
import enum
import typing


class ChoicesEnum(enum.Enum):
    @property
    @abc.abstractmethod
    def display(self) -> str:
        ...

    # This is to trick MyPy into understanding that we're
    # returning a valid, non-abstract subclass of `ChoicesEnum`,
    # which it can't understand if we call `enum_cls(value)`
    # directly.
    @classmethod
    def from_value(cls, value: typing.Any) -> "ChoicesEnum":
        return cls(value)


class IntChoicesEnum(int, ChoicesEnum):
    pass


class StrChoicesEnum(str, ChoicesEnum):
    pass