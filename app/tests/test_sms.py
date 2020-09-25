from airq.models.clients import Client
from airq.models.events import Event
from airq.models.events import EventType
from airq.models.requests import Request
from tests.base import BaseTestCase


class SMSTestCase(BaseTestCase):
    def test_get_quality(self):
        response = self.client.post(
            "/sms", data={"Body": "00000", "From": "+12222222222"}
        )
        self.assertEqual(200, response.status_code)
        self.assertEqual(1, Client.query.count())
        self.assertEqual(0, Event.query.count())
        self.assertEqual(0, Request.query.get_total_count())
        self.assert_twilio_response(
            "Hmm. Are you sure 00000 is a valid US zipcode?", response.data
        )

        response = self.client.post(
            "/sms", data={"Body": "97204", "From": "+12222222222"}
        )
        self.assertEqual(200, response.status_code)
        self.assertEqual(1, Client.query.count())
        self.assertEqual(1, Event.query.count())
        self.assertEqual(1, Request.query.get_total_count())
        self.assert_twilio_response(
            "Portland 97204 is GOOD (AQI 33).\n"
            "\n"
            "We'll alert you when the air quality changes category.\n"
            "Reply M for menu, U to stop this alert.",
            response.data,
        )

        client_id = Client.query.filter_by(identifier="+12222222222").first().id
        self.assert_event(client_id, EventType.QUALITY, zipcode="97204", pm25=7.945)

        response = self.client.post("/sms", data={"Body": "2", "From": "+12222222222"})
        self.assertEqual(200, response.status_code)
        self.assertEqual(1, Client.query.count())
        self.assertEqual(2, Event.query.count())
        self.assertEqual(2, Request.query.get_total_count())
        self.assert_twilio_response("Portland 97204 is GOOD (AQI 33).", response.data)
        self.assert_event(client_id, EventType.LAST, zipcode="97204", pm25=7.945)

        response = self.client.post("/sms", data={"Body": "1", "From": "+12222222222"})
        self.assertEqual(200, response.status_code)
        self.assertEqual(1, Client.query.count())
        self.assertEqual(3, Event.query.count())
        self.assertEqual(3, Request.query.get_total_count())
        self.assert_twilio_response(
            "GOOD (AQI: 0 - 50) means air quality is considered satisfactory, and air pollution poses little or no risk.\n"
            "\n"
            "Average PM2.5 from 8 sensor(s) near 97204 is 7.945 ug/m^3.",
            response.data,
        )
        self.assert_event(
            client_id,
            EventType.DETAILS,
            zipcode="97204",
            pm25=7.945,
            num_sensors=8,
            recommendations=[],
        )

        response = self.client.post(
            "/sms", data={"Body": "97038", "From": "+13333333333"}
        )
        self.assertEqual(200, response.status_code)
        self.assertEqual(2, Client.query.count())
        self.assertEqual(4, Event.query.count())
        self.assertEqual(4, Request.query.get_total_count())
        self.assert_twilio_response(
            "Molalla 97038 is MODERATE (AQI 98).\n"
            "\n"
            "We'll alert you when the air quality changes category.\n"
            "Reply M for menu, U to stop this alert.",
            response.data,
        )

        client_id = Client.query.filter_by(identifier="+13333333333").first().id
        self.assert_event(client_id, EventType.QUALITY, zipcode="97038", pm25=34.655)

        response = self.client.post("/sms", data={"Body": "2", "From": "+13333333333"})
        self.assertEqual(200, response.status_code)
        self.assertEqual(2, Client.query.count())
        self.assertEqual(5, Event.query.count())
        self.assertEqual(5, Request.query.get_total_count())
        self.assert_twilio_response(
            "Molalla 97038 is MODERATE (AQI 98).", response.data
        )
        self.assert_event(client_id, EventType.LAST, zipcode="97038", pm25=34.655)

        response = self.client.post("/sms", data={"Body": "1", "From": "+13333333333"})
        self.assertEqual(200, response.status_code)
        self.assertEqual(2, Client.query.count())
        self.assertEqual(6, Event.query.count())
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
        self.assert_event(
            client_id,
            EventType.DETAILS,
            zipcode="97038",
            pm25=34.655,
            num_sensors=2,
            recommendations=["97023", "97068", "97027"],
        )

        self.clock.advance()
        response = self.client.post(
            "/sms", data={"Body": "97038", "From": "+13333333333"}
        )
        self.assertEqual(200, response.status_code)
        self.assertEqual(2, Client.query.count())
        self.assertEqual(7, Event.query.count())
        self.assertEqual(7, Request.query.get_total_count())
        self.assert_twilio_response(
            "Molalla 97038 is MODERATE (AQI 98).", response.data
        )
        self.assert_event(client_id, EventType.QUALITY, zipcode="97038", pm25=34.655)

    def test_get_menu(self):
        response = self.client.post("/sms", data={"Body": "M", "From": "+13333333333"})
        self.assertEqual(200, response.status_code)
        self.assertEqual(1, Client.query.count())
        self.assertEqual(1, Event.query.count())
        self.assertEqual(0, Request.query.get_total_count())
        self.assert_twilio_response(
            "Reply\n"
            "1. Details and recommendations\n"
            "2. Current AQI\n"
            "3. Hazebot info\n"
            "4. Give feedback\n"
            "\n"
            "Or, enter a new zipcode.",
            response.data,
        )
        client_id = Client.query.filter_by(identifier="+13333333333").first().id
        self.assert_event(client_id, EventType.MENU)

    def test_get_info(self):
        response = self.client.post("/sms", data={"Body": "3", "From": "+13333333333"})
        self.assertEqual(200, response.status_code)
        self.assertEqual(1, Client.query.count())
        self.assertEqual(1, Event.query.count())
        self.assertEqual(0, Request.query.get_total_count())
        self.assert_twilio_response(
            "hazebot runs on PurpleAir sensor data and is a free service providing accessible local air quality information. "
            "Visit hazebot.org or email info@hazebot.org for feedback.",
            response.data,
        )
        client_id = Client.query.filter_by(identifier="+13333333333").first().id
        self.assert_event(client_id, EventType.ABOUT)

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
        self.assertEqual(1, Event.query.count())
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
        self.assert_event(client.id, EventType.QUALITY, zipcode="97204", pm25=7.945)

        response = self.client.post("/sms", data={"Body": "U", "From": "+12222222222"})
        self.assertEqual(200, response.status_code)
        self.assertEqual(1, Client.query.count())
        self.assertEqual(2, Event.query.count())
        self.assertEqual(1, Request.query.get_total_count())
        self.assert_twilio_response(
            "Got it! "
            "You will no longer recieve alerts for 97204. "
            "Text another zipcode if you'd like updates or reply M for menu.",
            response.data,
        )

        self.assertEqual("97204", client.zipcode.zipcode)
        self.assertEqual(self.timestamp, client.alerts_disabled_at)
        self.assert_event(client.id, EventType.UNSUBSCRIBE, zipcode="97204")
        response = self.client.post(
            "/sms", data={"Body": "97204", "From": "+12222222222"}
        )
        self.assertEqual(200, response.status_code)
        self.assertEqual(1, Client.query.count())
        self.assertEqual(3, Event.query.count())
        self.assertEqual(2, Request.query.get_total_count())
        self.assert_twilio_response(
            "Portland 97204 is GOOD (AQI 33).\n"
            "\n"
            'Alerting is disabled. Text "Y" to re-enable alerts when air quality changes.',
            response.data,
        )

        client = Client.query.first()
        self.assertEqual("97204", client.zipcode.zipcode)
        self.assertEqual(self.timestamp, client.alerts_disabled_at)
        self.assert_event(client.id, EventType.QUALITY, zipcode="97204", pm25=7.945)

        response = self.client.post("/sms", data={"Body": "Y", "From": "+12222222222"})
        self.assertEqual(200, response.status_code)
        self.assertEqual(1, Client.query.count())
        self.assertEqual(4, Event.query.count())
        self.assertEqual(2, Request.query.get_total_count())
        self.assert_twilio_response(
            "Got it! We'll send you timely alerts when air quality in 97204 changes category.",
            response.data,
        )

        self.assertEqual("97204", client.zipcode.zipcode)
        self.assertEqual(0, client.alerts_disabled_at)
        self.assert_event(client.id, EventType.RESUBSCRIBE, zipcode="97204")

        response = self.client.post("/sms", data={"Body": "Y", "From": "+12222222222"})
        self.assertEqual(200, response.status_code)
        self.assertEqual(1, Client.query.count())
        self.assertEqual(4, Event.query.count())
        self.assertEqual(2, Request.query.get_total_count())
        self.assert_twilio_response(
            "Looks like you're already watching 97204.",
            response.data,
        )

    def test_feedback(self):
        # Give feedback before feedback begin command
        response = self.client.post(
            "/sms", data={"Body": "Blah Blah Blah", "From": "+13333333333"}
        )
        client_id = Client.query.filter_by(identifier="+13333333333").first().id

        self.assertEqual(200, response.status_code)
        self.assertEqual(1, Client.query.count())
        self.assertEqual(0, Event.query.count())
        self.assertEqual(0, Request.query.get_total_count())
        self.assert_twilio_response(
            'Unrecognized option "Blah Blah Blah". Reply with M for the menu.',
            response.data,
        )

        # Go through feedback flow
        self.clock.advance()
        response = self.client.post("/sms", data={"Body": "4", "From": "+13333333333"})
        self.assertEqual(200, response.status_code)
        self.assertEqual(1, Client.query.count())
        self.assertEqual(1, Event.query.count())
        self.assertEqual(0, Request.query.get_total_count())
        self.assert_twilio_response(
            "Please enter your feedback below:",
            response.data,
        )
        self.assert_event(client_id, EventType.FEEDBACK_BEGIN)

        self.clock.advance()
        response = self.client.post(
            "/sms", data={"Body": "Blah Blah Blah", "From": "+13333333333"}
        )
        self.assertEqual(200, response.status_code)
        self.assertEqual(1, Client.query.count())
        self.assertEqual(2, Event.query.count())
        self.assertEqual(0, Request.query.get_total_count())
        self.assert_twilio_response("Thank you for your feedback!", response.data)
        self.assert_event(
            client_id, EventType.FEEDBACK_RECEIVED, feedback="Blah Blah Blah"
        )

        # try to post feedback again
        self.clock.advance()
        response = self.client.post(
            "/sms", data={"Body": "Blah Blah Blah", "From": "+13333333333"}
        )
        self.assertEqual(200, response.status_code)
        self.assertEqual(1, Client.query.count())
        self.assertEqual(2, Event.query.count())
        self.assertEqual(0, Request.query.get_total_count())
        self.assert_twilio_response(
            'Unrecognized option "Blah Blah Blah". Reply with M for the menu.',
            response.data,
        )
