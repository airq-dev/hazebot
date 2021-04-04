from airq.lib.client_preferences import IntegerChoicesPreference
from airq.lib.client_preferences import StringChoicesPreference
from airq.lib.readings import ConversionStrategy
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
        self.assertEqual(0, pref.clean("1"))
        self.assertEqual(12, pref.clean("2"))

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


class StringChoicesPreferenceTestCase(BaseTestCase):
    @staticmethod
    def _get_pref() -> StringChoicesPreference[ConversionStrategy]:
        return StringChoicesPreference(
            display_name="Foo Bar",
            description="Testing 123",
            default=ConversionStrategy.NONE,
            choices=ConversionStrategy,
        )

    def test_clean(self):
        pref = self._get_pref()
        self.assertIsNone(pref.clean("0"))
        self.assertIsNone(pref.clean("20"))
        self.assertEqual(ConversionStrategy.NONE, pref.clean("1"))
        self.assertEqual(ConversionStrategy.US_EPA, pref.clean("2"))

    def test_get_prompt(self):
        pref = self._get_pref()
        self.assertEqual(
            "Select one of\n"
            "1 - None\n"
            "2 - {}".format(ConversionStrategy.US_EPA.display),
            pref.get_prompt(),
        )
