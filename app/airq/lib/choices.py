import abc
import enum
import typing


class ChoicesEnum(enum.Enum):
    @property
    @abc.abstractmethod
    def display(self) -> str:
        ...

    @classmethod
    def from_name(cls, name: str) -> typing.Optional["ChoicesEnum"]:
        for m in cls:
            if m.name == name:
                return m
        return None

    @classmethod
    def from_display(cls, display: str) -> typing.Optional["ChoicesEnum"]:
        for m in cls:
            if m.display == display:
                return m
        return None
