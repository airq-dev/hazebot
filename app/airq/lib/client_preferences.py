import abc
import collections
import typing

from flask_babel import gettext

from airq.lib.logging import get_airq_logger


if typing.TYPE_CHECKING:
    from airq.models.clients import Client


logger = get_airq_logger(__name__)


TPreferenceValue = typing.TypeVar("TPreferenceValue", int, str)


# TODO: We could probably make this more type safe.
class ClientPreference(abc.ABC, typing.Generic[TPreferenceValue]):
    def __init__(
        self,
        display_name: str,
        description: str,
        default: TPreferenceValue,
    ):
        self.display_name = display_name
        self.description = description
        self.default: TPreferenceValue = default

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.name}, {self.display_name}, {self.description}, {self.default})"

    def __get__(
        self, instance: "Client", owner: typing.Type["Client"]
    ) -> TPreferenceValue:
        if instance is not None:
            return self.from_client(instance)
        return self

    def __set_name__(self, owner: typing.Type["Client"], name: str) -> None:
        ClientPreferencesRegistry.register_pref(name, self)

    @property
    def name(self) -> str:
        return ClientPreferencesRegistry.get_name(self)

    @abc.abstractmethod
    def validate(self, value: str) -> typing.Optional[TPreferenceValue]:
        """Ensure that the raw value is valid for this pref."""

    @abc.abstractmethod
    def from_client(self, client: "Client") -> typing.Any:
        """Get the value from the client."""

    @abc.abstractmethod
    def format_value(self, value: TPreferenceValue) -> str:
        """Make the raw value comprehensible by an end user."""

    @abc.abstractmethod
    def get_prompt(str) -> str:
        """Get a prompt for the user to fill in this preference."""


class IntegerChoicesPreference(ClientPreference[int]):
    def __init__(
        self,
        display_name: str,
        description: str,
        default: int,
        choices: typing.Iterable[int],
        choice_names: typing.Optional[typing.Dict[int, str]] = None,
    ):
        super().__init__(display_name, description, default)
        self._choices: typing.List[int] = list(choices)
        self._choice_names: typing.Dict[int, str] = choice_names or {}

    def from_client(self, client: "Client") -> int:
        value = client.get_pref(self.name)
        if not isinstance(value, int):
            raise RuntimeError(f"Unexpected pref {value} for {client}")
        return value

    def format_value(self, value: int) -> str:
        return self._choice_names.get(value, str(value))

    def validate(self, value: str) -> typing.Optional[int]:
        try:
            idx = int(value)
            if idx <= 0:
                return None
            return self._choices[idx - 1]
        except (IndexError, TypeError, ValueError):
            return None

    def get_prompt(self) -> str:
        prompt = [gettext("Select one of")]
        for i, choice in enumerate(self._choices, start=1):
            prompt.append(f"{i} - {self.format_value(choice)}")
        return "\n".join(prompt)


class IntegerPreference(ClientPreference[int]):
    def __init__(
        self,
        display_name: str,
        description: str,
        default: int,
        min_value: typing.Optional[int] = None,
        max_value: typing.Optional[int] = None,
    ):
        super().__init__(display_name, description, default)
        self._min_value = min_value
        self._max_value = max_value
        if self._min_value and self._max_value:
            if self._max_value >= self._max_value:
                raise RuntimeError(
                    f"Invalid min and max values {self._min_value} and {self._max_value}"
                )

    def from_client(self, client: "Client") -> int:
        v: typing.Union[str, int] = client.get_pref(self.name)
        if not isinstance(v, int):
            raise RuntimeError(f"Invalid pref value {v} for {self.name} for {client}")
        return v

    def format_value(self, value: int) -> str:
        return str(value)

    def validate(self, value: str) -> typing.Optional[int]:
        try:
            v = int(value)
        except (TypeError, ValueError):
            return None

        if self._min_value is not None and v < self._min_value:
            return None

        if self._max_value is not None and v > self._max_value:
            return None

        return v

    def get_prompt(self) -> str:
        if self._min_value is not None and self._max_value is not None:
            return gettext(
                "Enter an integer between %(min_value)s and %(max_value)s.",
                min_value=self._min_value,
                max_value=self._max_value,
            )
        if self._min_value is not None:
            return gettext(
                "Enter an integer greater than or equal to %(min_value)s.",
                min_value=self._min_value,
            )
        if self._max_value is not None:
            return gettext(
                "Enter an integer less than or equal to %(max_value)s.",
                max_value=self._max_value,
            )
        return gettext("Enter an integer.")


# TODO: Consider using singleton pattern
class ClientPreferencesRegistry:
    _prefs: typing.MutableMapping[str, ClientPreference] = collections.OrderedDict()

    @classmethod
    def register_pref(cls, name: str, pref: ClientPreference) -> None:
        assert name is not None, "Name unexpectedly None"
        if name in cls._prefs:
            raise RuntimeError("Can't double-register pref {}".format(pref.name))
        cls._prefs[name] = pref

    @classmethod
    def get_name(cls, pref: ClientPreference) -> str:
        for name, p in cls._prefs.items():
            if p is pref:
                return name
        raise RuntimeError("%s is not registered", pref)

    @classmethod
    def get_by_name(cls, name: str) -> ClientPreference:
        return cls._prefs[name]

    @classmethod
    def get_default(cls, name: str) -> typing.Union[str, int]:
        return cls.get_by_name(name).default

    @classmethod
    def iter_with_index(cls) -> typing.Iterator[typing.Tuple[int, ClientPreference]]:
        return enumerate(cls._prefs.values(), start=1)

    @classmethod
    def get_by_index(cls, index: int) -> typing.Optional[ClientPreference]:
        for i, pref in cls.iter_with_index():
            if i == index:
                return pref
        return None
