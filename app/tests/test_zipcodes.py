from airq.lib.readings import ConversionFactor
from airq.models.zipcodes import Zipcode
from tests.base import BaseTestCase


class ZipcodeTestCase(BaseTestCase):
    def test_get_aqi(self):
        zipcode = Zipcode.query.filter_by(zipcode="97204").first()
        self.assertEqual(
            zipcode.get_aqi(ConversionFactor.NONE),
            zipcode.get_readings().get_aqi(ConversionFactor.NONE),
        )
        self.assertEqual(
            zipcode.get_aqi(ConversionFactor.US_EPA),
            zipcode.get_readings().get_aqi(ConversionFactor.US_EPA),
        )

    def test_get_pm25(self):
        zipcode = Zipcode.query.filter_by(zipcode="97204").first()
        self.assertEqual(
            zipcode.get_pm25(ConversionFactor.NONE),
            zipcode.get_readings().get_pm25(ConversionFactor.NONE),
        )
        self.assertEqual(
            zipcode.get_pm25(ConversionFactor.US_EPA),
            zipcode.get_readings().get_pm25(ConversionFactor.US_EPA),
        )

    def test_get_pm25_level(self):
        zipcode = Zipcode.query.filter_by(zipcode="97204").first()
        self.assertEqual(
            zipcode.get_pm25_level(ConversionFactor.NONE),
            zipcode.get_readings().get_pm25_level(ConversionFactor.NONE),
        )
        self.assertEqual(
            zipcode.get_pm25_level(ConversionFactor.US_EPA),
            zipcode.get_readings().get_pm25_level(ConversionFactor.US_EPA),
        )

    def test_get_recommendations(self):
        zipcode = Zipcode.query.filter_by(zipcode="97204").first()
        self.assertListEqual(
            [], zipcode.get_recommendations(3, ConversionFactor.NONE)
        )

        zipcode = Zipcode.query.filter_by(zipcode="97038").first()
        self.assertListEqual(
            [
                Zipcode.query.filter_by(zipcode="97023").first(),
                Zipcode.query.filter_by(zipcode="97027").first(),
                Zipcode.query.filter_by(zipcode="97022").first(),
            ],
            zipcode.get_recommendations(3, ConversionFactor.NONE),
        )
