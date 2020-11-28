import abc
import collections
import typing

from flask_babel import gettext
from flask_babel import lazy_gettext

from airq.lib.choices import ChoicesEnum
from airq.lib.readings import Pm25


class ClientPreference(abc.ABC):
    def __init__(
        self,
        name: str,
        display_name: str,
        description: str,
        default: str,
    ):
        self.name = name
        self.display_name = display_name
        self.description = description
        self.default = default

    @abc.abstractmethod
    def validate(self, value: str) -> typing.Optional[str]:
        """Ensure that the raw value is valid for this pref."""

    @abc.abstractmethod
    def format_value(self, value: str) -> str:
        """Make the raw value comprehensible by an end user."""

    @abc.abstractmethod
    def get_prompt(str) -> str:
        """Get a prompt for the user to fill in this preference."""


class ChoicesPreference(ClientPreference):
    def __init__(
        self,
        name: str,
        display_name: str,
        description: str,
        default: str,
        choices: typing.Type[ChoicesEnum],
    ):
        super().__init__(name, display_name, description, default)
        self._enum = choices

    def _get_choices(self) -> typing.List[str]:
        return [c.display for c in sorted(self._enum)]

    def format_value(self, value: str) -> str:
        return self._enum.from_name(value).display

    def validate(self, value: str) -> typing.Optional[str]:
        choices = list(self._enum)
        try:
            idx = int(value)
            if idx <= 0:
                return None
            return choices[idx - 1].name
        except (IndexError, TypeError, ValueError):
            return None

    def get_prompt(self) -> str:
        prompt = [gettext("Select one of")]
        for i, choice in enumerate(self._get_choices(), start=1):
            prompt.append(f"{i} - {choice}")
        return "\n".join(prompt)


# TODO: Consider using singleton pattern
class ClientPreferencesConfig:
    _prefs: typing.MutableMapping[str, ClientPreference] = collections.OrderedDict()

    @classmethod
    def register_pref(cls, pref: ClientPreference) -> None:
        if pref.name in cls._prefs:
            raise RuntimeError("Can't double-register pref {}".format(pref.name))
        cls._prefs[pref.name] = pref

    @classmethod
    def get_by_name(cls, name: str) -> ClientPreference:
        return cls._prefs[name]

    @classmethod
    def iter_with_index(cls) -> typing.Iterator[typing.Tuple[int, ClientPreference]]:
        return enumerate(cls._prefs.values(), start=1)

    @classmethod
    def get_by_index(cls, index: int) -> typing.Optional[ClientPreference]:
        for i, pref in cls.iter_with_index():
            if i == index:
                return pref
        return None


ClientPreferencesConfig.register_pref(
    ChoicesPreference(
        name="alerting_threshold",
        display_name=lazy_gettext("Alerting Threshold"),
        description=lazy_gettext(
            "AQI category below which Hazebot won't send alerts.\n"
            "For example, if you set this to MODERATE, "
            "Hazebot won't send alerts when AQI transitions from GOOD to MODERATE or from MODERATE to GOOD."
        ),
        default=Pm25.GOOD.name,
        choices=Pm25,
    ),
)
# TODO: More prefs; e.g., a pref to set the alerting schedule and a pref for the conversion factor
