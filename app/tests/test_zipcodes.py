from airq.lib.readings import ConversionStrategy
from airq.models.zipcodes import Zipcode
from tests.base import BaseTestCase


class ZipcodeTestCase(BaseTestCase):
    def test_get_recommendations(self):
        zipcode = Zipcode.query.filter_by(zipcode="97204").first()
        self.assertListEqual(
            [], zipcode.get_recommendations(3, ConversionStrategy.NONE)
        )

        zipcode = Zipcode.query.filter_by(zipcode="97038").first()
        self.assertListEqual(
            [
                Zipcode.query.filter_by(zipcode="97023").first(),
                Zipcode.query.filter_by(zipcode="97027").first(),
                Zipcode.query.filter_by(zipcode="97022").first(),
            ],
            zipcode.get_recommendations(3, ConversionStrategy.NONE),
        )
