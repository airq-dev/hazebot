from airq.lib.client_preferences import IntegerChoicesPreference
from airq.lib.client_preferences import StringChoicesPreference
from airq.lib.readings import ConversionFactor
from airq.lib.readings import Pm25
from tests.base import BaseTestCase


class IntegerChoicesPreferenceTestCase(BaseTestCase):
    @staticmethod
    def _get_pref() -> IntegerChoicesPreference[Pm25]:
        return IntegerChoicesPreference(
            display_name="Foo Bar",
            description="Testing 123",
            default=Pm25.UNHEALTHY,
            choices=Pm25,
        )

    def test_clean(self):
        pref = self._get_pref()
        self.assertIsNone(pref.clean("0"))
        self.assertIsNone(pref.clean("20"))
        self.assertEqual(0, pref.clean("A"))
        self.assertEqual(12, pref.clean("B"))

    def test_get_prompt(self):
        pref = self._get_pref()
        self.assertEqual(
            "Select one of\n"
            "A - GOOD\n"
            "B - MODERATE\n"
            "C - UNHEALTHY FOR SENSITIVE GROUPS\n"
            "D - UNHEALTHY\n"
            "E - VERY UNHEALTHY\n"
            "F - HAZARDOUS",
            pref.get_prompt(),
        )


class StringChoicesPreferenceTestCase(BaseTestCase):
    @staticmethod
    def _get_pref() -> StringChoicesPreference[ConversionFactor]:
        return StringChoicesPreference(
            display_name="Foo Bar",
            description="Testing 123",
            default=ConversionFactor.NONE,
            choices=ConversionFactor,
        )

    def test_clean(self):
        pref = self._get_pref()
        self.assertIsNone(pref.clean("0"))
        self.assertIsNone(pref.clean("20"))
        self.assertEqual(ConversionFactor.NONE, pref.clean("A"))
        self.assertEqual(ConversionFactor.US_EPA, pref.clean("B"))

    def test_get_prompt(self):
        pref = self._get_pref()
        self.assertEqual(
            "Select one of\n"
            "A - None\n"
            "B - {}".format(ConversionFactor.US_EPA.display),
            pref.get_prompt(),
        )
