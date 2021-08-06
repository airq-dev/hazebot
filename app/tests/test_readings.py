from airq.lib.readings import ConversionFactor
from airq.lib.readings import Readings
from airq.lib.readings import _pm25_to_aqi
from tests.base import BaseTestCase


class ReadingsTestCase(BaseTestCase):
    def test_readings_get_pm25(self):
        readings = Readings(pm25=20.3, pm_cf_1=24.0, humidity=28)
        self.assertEqual(
            readings.get_pm25(ConversionFactor.NONE),
            ConversionFactor.NONE.convert(readings),
        )
        self.assertEqual(
            readings.get_pm25(ConversionFactor.US_EPA),
            ConversionFactor.US_EPA.convert(readings),
        )

    def test_conversion_factor_convert(self):
        self.assertEqual(
            21,
            _pm25_to_aqi(
                ConversionFactor.US_EPA.convert(
                    Readings(pm25=7.03, pm_cf_1=7.03, humidity=54)
                )
            ),
        )

        self.assertEqual(
            68,
            _pm25_to_aqi(
                ConversionFactor.US_EPA.convert(
                    Readings(pm25=29.88, pm_cf_1=35.41, humidity=53)
                )
            ),
        )
