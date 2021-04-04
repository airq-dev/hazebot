from airq.lib.readings import ConversionStrategy
from airq.lib.readings import Readings
from airq.lib.readings import _pm25_to_aqi
from tests.base import BaseTestCase


class ReadingsTestCase(BaseTestCase):
    def test_readings_get_pm25(self):
        readings = Readings(pm25=20.3, pm_cf_1=24.0, humidity=28)
        self.assertEqual(
            readings.get_pm25(ConversionStrategy.NONE),
            ConversionStrategy.NONE.convert(readings),
        )
        self.assertEqual(
            readings.get_pm25(ConversionStrategy.US_EPA),
            ConversionStrategy.US_EPA.convert(readings),
        )

    def test_conversion_strategy_convert(self):
        self.assertEqual(
            21,
            _pm25_to_aqi(
                ConversionStrategy.US_EPA.convert(
                    Readings(pm25=7.03, pm_cf_1=7.03, humidity=54)
                )
            ),
        )

        self.assertEqual(
            68,
            _pm25_to_aqi(
                ConversionStrategy.US_EPA.convert(
                    Readings(pm25=29.88, pm_cf_1=35.41, humidity=53)
                )
            ),
        )
