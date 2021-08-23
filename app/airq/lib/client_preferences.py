import abc
import collections
import string
import typing

from flask_babel import gettext
from sqlalchemy.orm.attributes import flag_modified

from airq.config import db
from airq.lib.choices import ChoicesEnum
from airq.lib.choices import IntChoicesEnum
from airq.lib.choices import StrChoicesEnum


if typing.TYPE_CHECKING:
    from airq.models.clients import Client


class InvalidPrefValue(Exception):
    """This pref value is invalid."""


TPreferenceValue = typing.TypeVar(
    "TPreferenceValue", bound=typing.Union[int, str, ChoicesEnum]
)
TChoicesEnum = typing.TypeVar("TChoicesEnum", bound=ChoicesEnum)
TIntChoicesEnum = typing.TypeVar("TIntChoicesEnum", bound=IntChoicesEnum)
TStrChoicesEnum = typing.TypeVar("TStrChoicesEnum", bound=StrChoicesEnum)


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
            value = preferences.get(self.name)
            if value is not None:
                return self._cast(value)
            return self.default
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

    @abc.abstractmethod
    def _cast(self, value: typing.Any) -> TPreferenceValue:
        pass

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


class ChoicesPreference(typing.Generic[TChoicesEnum], ClientPreference[TChoicesEnum]):
    def __init__(
        self,
        display_name: str,
        description: str,
        default: TChoicesEnum,
        choices: typing.Type[TChoicesEnum],
    ):
        super().__init__(display_name, description, default)
        self._choices = choices

    def _get_choices_with_letters(self) -> typing.List[typing.Tuple[str, TChoicesEnum]]:
        choices: typing.List[TChoicesEnum] = self._choices
        out = []
        for i, choice in enumerate(choices):
            out.append((string.ascii_uppercase[i], choice))
        return out

    def _cast(self, value: typing.Any) -> TChoicesEnum:
        return self._choices.from_value(value)

    def format_value(self, value: TChoicesEnum) -> str:
        return value.display

    def clean(self, user_input: str) -> typing.Optional[TChoicesEnum]:
        return dict(self._get_choices_with_letters()).get(user_input.upper())

    def _validate(self, _value: TChoicesEnum):
        pass  # Valid by definition

    def get_prompt(self) -> str:
        prompt = [gettext("Select one of")]
        for letter, choice in self._get_choices_with_letters():
            prompt.append(f"{letter} - {choice.display}")
        return "\n".join(prompt)


class IntegerChoicesPreference(ChoicesPreference[TIntChoicesEnum]):
    pass


class StringChoicesPreference(ChoicesPreference[TStrChoicesEnum]):
    pass


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

    def _cast(self, value: typing.Any) -> int:
        assert isinstance(value, int)
        return value

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
    def iter_with_letters(cls) -> typing.Iterator[typing.Tuple[str, ClientPreference]]:
        return (
            (string.ascii_uppercase[i], name)
            for i, name in enumerate(cls._prefs.values())
        )

    @classmethod
    def get_by_letter(cls, letter: str) -> typing.Optional[ClientPreference]:
        for l, pref in cls.iter_with_letters():
            if l == letter:
                return pref
        return None
