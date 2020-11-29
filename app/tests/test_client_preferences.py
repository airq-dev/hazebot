from airq.lib.client_preferences import IntegerChoicesPreference
from airq.lib.readings import Pm25
from tests.base import BaseTestCase


class ChoicesPreferenceTestCase(BaseTestCase):
    @staticmethod
    def _get_pref() -> IntegerChoicesPreference:
        return IntegerChoicesPreference(
            display_name="Foo Bar",
            description="Testing 123",
            default=Pm25.UNHEALTHY.value,
            choices=sorted(c.value for c in Pm25),
            choice_names={c.value: c.display for c in Pm25},
        )

    def test_validate(self):
        pref = self._get_pref()
        self.assertIsNone(pref.validate("0"))
        self.assertIsNone(pref.validate("20"))
        self.assertEqual(0, pref.validate("1"))
        self.assertEqual(12, pref.validate("2"))

    def test_get_prompt(self):
        pref = self._get_pref()
        self.assertEqual(
            "Select one of\n"
            "1 - GOOD\n"
            "2 - MODERATE\n"
            "3 - UNHEALTHY FOR SENSITIVE GROUPS\n"
            "4 - UNHEALTHY\n"
            "5 - VERY UNHEALTHY\n"
            "6 - HAZARDOUS",
            pref.get_prompt(),
        )
