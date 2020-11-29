import abc
import collections
from enum import IntEnum
import typing

from flask_babel import gettext
from sqlalchemy.orm.attributes import flag_modified

from airq.config import db
from airq.lib.choices import IntChoicesEnum


if typing.TYPE_CHECKING:
    from airq.models.clients import Client


class InvalidPrefValue(Exception):
    """This pref value is invalid."""


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
            preferences = instance.preferences or {}
            return preferences.get(self.name, self.default)  # type: ignore
        return self

    def __set__(self, client: "Client", value: TPreferenceValue):
        self._set(client, value)

    def set_from_user_input(
        self, client: "Client", user_input: str
    ) -> TPreferenceValue:
        value = self.clean(user_input.strip())
        if value is None:
            msg = gettext(
                'Hmm, "%(input)s" doesn\'t seem to be a valid choice.',
                input=user_input[:20],
            )
            msg += "\n\n"
            msg += self.get_prompt()
            raise InvalidPrefValue(msg)
        self._set(client, value)
        db.session.commit()
        return value

    def _set(self, client: "Client", value: TPreferenceValue):
        self._validate(value)
        if client.preferences is None:
            client.preferences = {}
        client.preferences[self.name] = value  # type: ignore
        # SQLAlchemy doesn't pick up changes to JSON fields,
        # so we have to tell it what's going on. See
        # https://stackoverflow.com/questions/42559434/updates-to-json-field-dont-persist-to-db
        # for details.
        flag_modified(client, "preferences")
        db.session.add(client)

    def __set_name__(self, owner: typing.Type["Client"], name: str) -> None:
        ClientPreferencesRegistry.register_pref(name, self)

    @property
    def name(self) -> str:
        return ClientPreferencesRegistry.get_name(self)

    @abc.abstractmethod
    def clean(self, value: str) -> typing.Optional[TPreferenceValue]:
        """Coerce user input to a valid value for this pref, or throw an error."""

    @abc.abstractmethod
    def _validate(self, value: TPreferenceValue):
        """Ensure that the raw value is valid for this pref."""

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
        choices: typing.Type[IntChoicesEnum],
    ):
        super().__init__(display_name, description, default)
        self._choices = choices

    def _get_choices(self) -> typing.List[IntChoicesEnum]:
        return list(self._choices)

    def format_value(self, value: int) -> str:
        return self._choices.from_value(value).display

    def clean(self, user_input: str) -> typing.Optional[int]:
        choices = self._get_choices()
        try:
            idx = int(user_input)
            if idx <= 0:
                return None
            return choices[idx - 1].value
        except (IndexError, TypeError, ValueError):
            return None

    def _validate(self, value: int):
        if value not in self._get_choices():
            raise InvalidPrefValue()

    def get_prompt(self) -> str:
        prompt = [gettext("Select one of")]
        for i, choice in enumerate(self._get_choices(), start=1):
            prompt.append(f"{i} - {choice.display}")
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

    def format_value(self, value: int) -> str:
        return str(value)

    def clean(self, user_input: str) -> typing.Optional[int]:
        try:
            value = int(user_input)
            self._validate(value)
        except (TypeError, ValueError, InvalidPrefValue):
            return None
        return value

    def _validate(self, value: int):
        if self._min_value is not None and value < self._min_value:
            raise InvalidPrefValue()
        if self._max_value is not None and value > self._max_value:
            raise InvalidPrefValue()

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
