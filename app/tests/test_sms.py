from airq.models.clients import Client
from airq.models.requests import Request
from tests.base import BaseTestCase


class SMSTestCase(BaseTestCase):
    def test_get_quality(self):
        response = self.client.post(
            "/sms", data={"Body": "00000", "From": "+12222222222"}
        )
        self.assertEqual(200, response.status_code)
        self.assertEqual(1, Client.query.count())
        self.assertEqual(0, Request.query.get_total_count())
        self.assert_twilio_response(
            "Hmm. Are you sure 00000 is a valid US zipcode?", response.data
        )

        response = self.client.post(
            "/sms", data={"Body": "97204", "From": "+12222222222"}
        )
        self.assertEqual(200, response.status_code)
        self.assertEqual(1, Client.query.count())
        self.assertEqual(1, Request.query.get_total_count())
        self.assert_twilio_response(
            "Portland 97204 is GOOD (AQI 33).\n"
            "\n"
            "We'll alert you when the air quality changes category.\n"
            "Reply M for menu, U to stop this alert.",
            response.data,
        )

        response = self.client.post("/sms", data={"Body": "2", "From": "+12222222222"})
        self.assertEqual(200, response.status_code)
        self.assertEqual(1, Client.query.count())
        self.assertEqual(2, Request.query.get_total_count())
        self.assert_twilio_response("Portland 97204 is GOOD (AQI 33).", response.data)

        response = self.client.post("/sms", data={"Body": "1", "From": "+12222222222"})
        self.assertEqual(200, response.status_code)
        self.assertEqual(1, Client.query.count())
        self.assertEqual(3, Request.query.get_total_count())
        self.assert_twilio_response(
            "GOOD (AQI: 0 - 50) means air quality is considered satisfactory, and air pollution poses little or no risk.\n"
            "\n"
            "Average PM2.5 from 8 sensor(s) near 97204 is 7.945 ug/m^3.",
            response.data,
        )

        response = self.client.post(
            "/sms", data={"Body": "97038", "From": "+13333333333"}
        )
        self.assertEqual(200, response.status_code)
        self.assertEqual(2, Client.query.count())
        self.assertEqual(4, Request.query.get_total_count())
        self.assert_twilio_response(
            "Molalla 97038 is MODERATE (AQI 98).\n"
            "\n"
            "We'll alert you when the air quality changes category.\n"
            "Reply M for menu, U to stop this alert.",
            response.data,
        )

        response = self.client.post("/sms", data={"Body": "2", "From": "+13333333333"})
        self.assertEqual(200, response.status_code)
        self.assertEqual(2, Client.query.count())
        self.assertEqual(5, Request.query.get_total_count())
        self.assert_twilio_response(
            "Molalla 97038 is MODERATE (AQI 98).", response.data
        )

        response = self.client.post("/sms", data={"Body": "1", "From": "+13333333333"})
        self.assertEqual(200, response.status_code)
        self.assertEqual(2, Client.query.count())
        self.assertEqual(6, Request.query.get_total_count())
        self.assert_twilio_response(
            "MODERATE (AQI: 51 - 100) means air quality is acceptable; however, for some pollutants there may be a moderate health concern for a very small number of people who are unusually sensitive to air pollution."
            "\n\n"
            "Here are the closest places with better air quality:"
            "\n"
            " - Estacada 97023: GOOD (16.7 mi)\n"
            " - West Linn 97068: GOOD (17.3 mi)\n"
            " - Gladstone 97027: GOOD (18.5 mi)\n"
            "\n"
            "Average PM2.5 from 2 sensor(s) near 97038 is 34.655 ug/m^3.",
            response.data,
        )

        response = self.client.post(
            "/sms", data={"Body": "97038", "From": "+13333333333"}
        )
        self.assertEqual(200, response.status_code)
        self.assertEqual(2, Client.query.count())
        self.assertEqual(7, Request.query.get_total_count())
        self.assert_twilio_response(
            "Molalla 97038 is MODERATE (AQI 98).", response.data
        )

    def test_get_menu(self):
        response = self.client.post("/sms", data={"Body": "M", "From": "+13333333333"})
        self.assertEqual(200, response.status_code)
        self.assertEqual(1, Client.query.count())
        self.assertEqual(0, Request.query.get_total_count())
        self.assert_twilio_response(
            "Reply\n"
            "1. Details and recommendations\n"
            "2. Current AQI\n"
            "3. Hazebot info\n"
            "\n"
            "Or, enter a new zipcode.",
            response.data,
        )

    def test_get_info(self):
        response = self.client.post("/sms", data={"Body": "3", "From": "+13333333333"})
        self.assertEqual(200, response.status_code)
        self.assertEqual(1, Client.query.count())
        self.assertEqual(0, Request.query.get_total_count())
        self.assert_twilio_response(
            "hazebot runs on PurpleAir sensor data and is a free service providing accessible local air quality information. "
            "Visit hazebot.org or email info@hazebot.org for feedback.",
            response.data,
        )

    def test_unsubscribe(self):
        response = self.client.post("/sms", data={"Body": "U", "From": "+12222222222"})
        self.assertEqual(200, response.status_code)
        self.assertEqual(1, Client.query.count())
        self.assertEqual(0, Request.query.get_total_count())
        self.assert_twilio_response(
            "Looks like you haven't use hazebot before! "
            "Please text us a zipcode and we'll send you the air quality.",
            response.data,
        )

        response = self.client.post(
            "/sms", data={"Body": "97204", "From": "+12222222222"}
        )
        self.assertEqual(200, response.status_code)
        self.assertEqual(1, Client.query.count())
        self.assertEqual(1, Request.query.get_total_count())
        self.assert_twilio_response(
            "Portland 97204 is GOOD (AQI 33).\n"
            "\n"
            "We'll alert you when the air quality changes category.\n"
            "Reply M for menu, U to stop this alert.",
            response.data,
        )

        client = Client.query.first()
        self.assertEqual("97204", client.zipcode.zipcode)
        self.assertEqual(0, client.alerts_disabled_at)

        response = self.client.post("/sms", data={"Body": "U", "From": "+12222222222"})
        self.assertEqual(200, response.status_code)
        self.assertEqual(1, Client.query.count())
        self.assertEqual(1, Request.query.get_total_count())
        self.assert_twilio_response(
            "Got it! "
            "You will no longer recieve alerts for 97204. "
            "Text another zipcode if you'd like updates or reply M for menu.",
            response.data,
        )

        client = Client.query.first()
        self.assertEqual("97204", client.zipcode.zipcode)
        self.assertEqual(self.timestamp, client.alerts_disabled_at)
