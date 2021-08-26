from airq.lib.readings import Pm25
from airq.models.clients import Client
from airq.models.events import Event
from airq.models.events import EventType
from airq.tasks import bulk_send
from tests.base import BaseTestCase


class SMSTestCase(BaseTestCase):
    def _create_client(self) -> Client:
        self.client.post("/sms/en", data={"Body": "97204", "From": "+13333333333"})
        return Client.query.filter_by(identifier="+13333333333").first()

    def test_get_quality(self):
        response = self.client.post(
            "/sms/en", data={"Body": "00000", "From": "+12222222222"}
        )
        self.assertEqual(200, response.status_code)
        self.assertEqual(1, Client.query.count())
        self.assertEqual(0, Event.query.count())
        self.assert_twilio_response(
            "Hmm. Are you sure 00000 is a valid US zipcode?", response.data
        )

        response = self.client.post(
            "/sms/en", data={"Body": "97204", "From": "+12222222222"}
        )
        self.assertEqual(200, response.status_code)
        self.assertEqual(1, Client.query.count())
        self.assertEqual(1, Event.query.count())
        self.assert_twilio_response(
            "Welcome to Hazebot! We'll send you alerts when air quality in Portland 97204 changes category. Air quality is now GOOD (AQI 42).\n"
            "\n"
            'Save this contact and text us your zipcode whenever you\'d like an instant update. And you can always text "M" to see the whole menu.',
            response.data,
            media="localhost:8080/public/vcard/en.vcf",
        )

        client_id = Client.query.filter_by(identifier="+12222222222").first().id
        self.assert_event(client_id, EventType.QUALITY, zipcode="97204", pm25=9.875)

        response = self.client.post(
            "/sms/en", data={"Body": "2", "From": "+12222222222"}
        )
        self.assertEqual(200, response.status_code)
        self.assertEqual(1, Client.query.count())
        self.assertEqual(2, Event.query.count())
        self.assert_twilio_response(
            "Portland 97204 is GOOD (AQI 42).\n"
            "\n"
            'Text "M" for Menu, "E" to end alerts.',
            response.data,
        )
        self.assert_event(client_id, EventType.LAST, zipcode="97204", pm25=9.875)

        response = self.client.post(
            "/sms/en", data={"Body": "1", "From": "+12222222222"}
        )
        self.assertEqual(200, response.status_code)
        self.assertEqual(1, Client.query.count())
        self.assertEqual(3, Event.query.count())
        self.assert_twilio_response(
            "GOOD (AQI: 0 - 50) means air quality is considered satisfactory, and air pollution poses little or no risk.\n"
            "\n"
            "Average PM2.5 from 8 sensors near 97204 is 9.875 ug/m^3.",
            response.data,
        )
        self.assert_event(
            client_id,
            EventType.DETAILS,
            zipcode="97204",
            pm25=9.875,
            num_sensors=8,
            recommendations=[],
        )

        response = self.client.post(
            "/sms/en", data={"Body": "97038", "From": "+13333333333"}
        )
        self.assertEqual(200, response.status_code)
        self.assertEqual(2, Client.query.count())
        self.assertEqual(4, Event.query.count())
        self.assert_twilio_response(
            "Welcome to Hazebot! We'll send you alerts when air quality in Molalla 97038 changes category. Air quality is now MODERATE (AQI 74).\n"
            "\n"
            'Save this contact and text us your zipcode whenever you\'d like an instant update. And you can always text "M" to see the whole menu.',
            response.data,
            media="localhost:8080/public/vcard/en.vcf",
        )

        client_id = Client.query.filter_by(identifier="+13333333333").first().id
        self.assert_event(client_id, EventType.QUALITY, zipcode="97038", pm25=22.9)

        response = self.client.post(
            "/sms/en", data={"Body": "2", "From": "+13333333333"}
        )
        self.assertEqual(200, response.status_code)
        self.assertEqual(2, Client.query.count())
        self.assertEqual(5, Event.query.count())
        self.assert_twilio_response(
            "Molalla 97038 is MODERATE (AQI 74).\n"
            "\n"
            'Text "M" for Menu, "E" to end alerts.',
            response.data,
        )
        self.assert_event(client_id, EventType.LAST, zipcode="97038", pm25=22.9)

        response = self.client.post(
            "/sms/en", data={"Body": "1", "From": "+13333333333"}
        )
        self.assertEqual(200, response.status_code)
        self.assertEqual(2, Client.query.count())
        self.assertEqual(6, Event.query.count())
        self.assert_twilio_response(
            "MODERATE (AQI: 51 - 100) means air quality is acceptable; however, for some pollutants there may be a moderate health concern for a very small number of people who are unusually sensitive to air pollution."
            "\n\n"
            "Here are the closest places with better air quality:"
            "\n"
            " - Estacada 97023: GOOD (16.7 mi)\n"
            " - Gladstone 97027: GOOD (18.5 mi)\n"
            " - Eagle Creek 97022: GOOD (20.0 mi)\n"
            "\n"
            "Average PM2.5 from 3 sensors near 97038 is 22.9 ug/m^3.",
            response.data,
        )
        self.assert_event(
            client_id,
            EventType.DETAILS,
            zipcode="97038",
            pm25=22.9,
            num_sensors=3,
            recommendations=["97023", "97027", "97022"],
        )

        self.clock.advance()
        response = self.client.post(
            "/sms/en", data={"Body": "97038", "From": "+13333333333"}
        )
        self.assertEqual(200, response.status_code)
        self.assertEqual(2, Client.query.count())
        self.assertEqual(7, Event.query.count())
        self.assert_twilio_response(
            "Molalla 97038 is MODERATE (AQI 74).\n"
            "\n"
            'Text "M" for Menu, "E" to end alerts.',
            response.data,
        )
        self.assert_event(client_id, EventType.QUALITY, zipcode="97038", pm25=22.9)

        self.clock.advance()
        response = self.client.post(
            "/sms/en", data={"Body": "97204", "From": "+13333333333"}
        )
        self.assertEqual(200, response.status_code)
        self.assertEqual(2, Client.query.count())
        self.assertEqual(8, Event.query.count())
        self.assert_twilio_response(
            "Portland 97204 is GOOD (AQI 42).\n"
            "\n"
            "You are now receiving alerts for 97204.",
            response.data,
        )
        self.assert_event(client_id, EventType.QUALITY, zipcode="97204", pm25=9.875)

    def test_get_menu(self):
        expected_response = (
            "Reply\n"
            "1. Air recommendations\n"
            "2. Current AQI\n"
            "3. Set preferences\n"
            "4. About us\n"
            "5. Give feedback\n"
            "6. Stop alerts\n"
            "7. Donate\n"
            "\n"
            "Or, enter a new zipcode."
        )

        response = self.client.post(
            "/sms/en", data={"Body": "M", "From": "+13333333333"}
        )
        self.assertEqual(200, response.status_code)
        self.assertEqual(1, Client.query.count())
        self.assertEqual(1, Event.query.count())
        self.assert_twilio_response(expected_response, response.data)
        client_id = Client.query.filter_by(identifier="+13333333333").first().id
        self.assert_event(client_id, EventType.MENU)

        response = self.client.post(
            "/sms/en", data={"Body": "MENU", "From": "+13333333333"}
        )
        self.assertEqual(200, response.status_code)
        self.assertEqual(1, Client.query.count())
        self.assertEqual(2, Event.query.count())
        self.assert_twilio_response(expected_response, response.data)
        client_id = Client.query.filter_by(identifier="+13333333333").first().id
        self.assert_event(client_id, EventType.MENU)

    def test_get_info(self):
        response = self.client.post(
            "/sms/en", data={"Body": "4", "From": "+13333333333"}
        )
        self.assertEqual(200, response.status_code)
        self.assertEqual(1, Client.query.count())
        self.assertEqual(1, Event.query.count())
        self.assert_twilio_response(
            "hazebot runs on PurpleAir sensor data and is a free service. Reach us at hazebot.org or info@hazebot.org. Press 7 for information on how to support our work.",
            response.data,
        )
        client_id = Client.query.filter_by(identifier="+13333333333").first().id
        self.assert_event(client_id, EventType.ABOUT)

    def test_donate(self):
        response = self.client.post(
            "/sms/en", data={"Body": "7", "From": "+13333333333"}
        )
        self.assertEqual(200, response.status_code)
        self.assertEqual(1, Client.query.count())
        self.assertEqual(1, Event.query.count())
        self.assert_twilio_response(
            "Like this project? A few dollars allows hundreds of people to breathe easy with hazebot. Help us reach more by donating here: https://bit.ly/3bh0Cx9.",
            response.data,
        )
        client_id = Client.query.filter_by(identifier="+13333333333").first().id
        self.assert_event(client_id, EventType.DONATE)

        response = self.client.post(
            "/sms/en", data={"Body": "DoNaTe", "From": "+13333333333"}
        )
        self.assertEqual(200, response.status_code)
        self.assertEqual(1, Client.query.count())
        self.assertEqual(2, Event.query.count())
        self.assert_twilio_response(
            "Like this project? "
            "A few dollars allows hundreds of people to breathe easy with hazebot. "
            "Help us reach more by donating here: https://bit.ly/3bh0Cx9.",
            response.data,
        )
        client_id = Client.query.filter_by(identifier="+13333333333").first().id
        self.assert_event(client_id, EventType.DONATE)

    def test_unsubscribe(self):
        response = self.client.post(
            "/sms/en", data={"Body": "U", "From": "+12222222222"}
        )
        self.assertEqual(200, response.status_code)
        self.assertEqual(1, Client.query.count())
        self.assert_twilio_response(
            "Looks like you haven't use hazebot before! "
            "Please text us a zipcode and we'll send you the air quality.",
            response.data,
        )

        self.clock.advance()
        response = self.client.post(
            "/sms/en", data={"Body": "97204", "From": "+12222222222"}
        )
        self.assertEqual(200, response.status_code)
        self.assertEqual(1, Client.query.count())
        self.assertEqual(1, Event.query.count())
        self.assert_twilio_response(
            "Welcome to Hazebot! We'll send you alerts when air quality in Portland 97204 changes category. Air quality is now GOOD (AQI 42).\n"
            "\n"
            'Save this contact and text us your zipcode whenever you\'d like an instant update. And you can always text "M" to see the whole menu.',
            response.data,
            media="localhost:8080/public/vcard/en.vcf",
        )

        client = Client.query.first()
        self.assertEqual("97204", client.zipcode.zipcode)
        self.assertEqual(0, client.alerts_disabled_at)
        self.assert_event(client.id, EventType.QUALITY, zipcode="97204", pm25=9.875)

        alerts_disabled_at = self.clock.advance().timestamp()
        response = self.client.post(
            "/sms/en", data={"Body": "E", "From": "+12222222222"}
        )
        self.assertEqual(200, response.status_code)
        self.assertEqual(1, Client.query.count())
        self.assertEqual(2, Event.query.count())
        self.assert_twilio_response(
            "Got it! You will not receive air quality updates until you text a new zipcode.\n"
            "\n"
            "Tell us why you're leaving so we can improve our service:\n"
            "A. Air quality is not a concern in my area\n"
            "B. SMS texts are not my preferred information source\n"
            "C. Alerts are too frequent\n"
            "D. Information is inaccurate\n"
            "E. Other",
            response.data,
        )
        client = Client.query.first()
        self.assert_event(client.id, EventType.UNSUBSCRIBE, zipcode="97204")
        self.assertEqual("97204", client.zipcode.zipcode)
        self.assertEqual(alerts_disabled_at, client.alerts_disabled_at)

        # Give some feedback
        self.clock.advance()
        response = self.client.post(
            "/sms/en", data={"Body": "A", "From": "+12222222222"}
        )
        self.assertEqual(200, response.status_code)
        self.assertEqual(1, Client.query.count())
        self.assertEqual(3, Event.query.count())
        self.assert_twilio_response(
            "Thank you for your feedback!",
            response.data,
        )
        client = Client.query.first()
        self.assert_event(
            client.id,
            EventType.FEEDBACK_RECEIVED,
            feedback="Air quality is not a concern in my area",
        )

        self.clock.advance()
        response = self.client.post(
            "/sms/en", data={"Body": "97204", "From": "+12222222222"}
        )
        self.assertEqual(200, response.status_code)
        self.assertEqual(1, Client.query.count())
        self.assertEqual(4, Event.query.count())
        self.assert_twilio_response(
            "Portland 97204 is GOOD (AQI 42).\n"
            "\n"
            'Alerting is disabled. Text "Y" to re-enable alerts when air quality changes.',
            response.data,
        )

        client = Client.query.first()
        self.assertEqual("97204", client.zipcode.zipcode)
        self.assertEqual(alerts_disabled_at, client.alerts_disabled_at)
        self.assert_event(client.id, EventType.QUALITY, zipcode="97204", pm25=9.875)

        self.clock.advance()
        response = self.client.post(
            "/sms/en", data={"Body": "Y", "From": "+12222222222"}
        )
        self.assertEqual(200, response.status_code)
        self.assertEqual(1, Client.query.count())
        self.assertEqual(5, Event.query.count())
        self.assert_twilio_response(
            "Got it! We'll send you timely alerts when air quality in 97204 changes category.",
            response.data,
        )

        client = Client.query.first()
        self.assertEqual("97204", client.zipcode.zipcode)
        self.assertEqual(0, client.alerts_disabled_at)
        self.assert_event(client.id, EventType.RESUBSCRIBE, zipcode="97204")

        self.clock.advance()
        response = self.client.post(
            "/sms/en", data={"Body": "Y", "From": "+12222222222"}
        )
        self.assertEqual(200, response.status_code)
        self.assertEqual(1, Client.query.count())
        self.assertEqual(5, Event.query.count())
        self.assert_twilio_response(
            "Looks like you're already watching 97204.",
            response.data,
        )

        # Now test that we can send the alert
        self.clock.advance()
        client = Client.query.first()
        client.last_pm25 += 50
        self.db.session.commit()
        self.assertTrue(client.maybe_notify())
        self.assertEqual(6, Event.query.count())
        self.assert_event(
            client.id,
            EventType.ALERT,
            zipcode=client.zipcode.zipcode,
            pm25=client.last_pm25,
        )

        alerts_disabled_at = self.clock.advance().timestamp()
        response = self.client.post(
            "/sms/en", data={"Body": "END", "From": "+12222222222"}
        )
        self.assertEqual(200, response.status_code)
        self.assertEqual(1, Client.query.count())
        self.assertEqual(7, Event.query.count())
        self.assert_twilio_response(
            "Got it! You will not receive air quality updates until you text a new zipcode.\n"
            "\n"
            "Tell us why you're leaving so we can improve our service:\n"
            "A. Air quality is not a concern in my area\n"
            "B. SMS texts are not my preferred information source\n"
            "C. Alerts are too frequent\n"
            "D. Information is inaccurate\n"
            "E. Other",
            response.data,
        )
        client = Client.query.first()
        self.assert_event(client.id, EventType.UNSUBSCRIBE, zipcode="97204")
        self.assertEqual("97204", client.zipcode.zipcode)
        self.assertEqual(alerts_disabled_at, client.alerts_disabled_at)

        self.clock.advance()
        response = self.client.post(
            "/sms/en", data={"Body": "E", "From": "+12222222222"}
        )
        self.assertEqual(200, response.status_code)
        self.assertEqual(1, Client.query.count())
        self.assertEqual(7, Event.query.count())
        self.assert_twilio_response(
            "Please enter your feedback below:",
            response.data,
        )
        client = Client.query.first()
        self.assert_event(client.id, EventType.UNSUBSCRIBE, zipcode="97204")
        self.assertEqual("97204", client.zipcode.zipcode)
        self.assertEqual(alerts_disabled_at, client.alerts_disabled_at)

        self.clock.advance()
        response = self.client.post(
            "/sms/en", data={"Body": "foobar", "From": "+12222222222"}
        )
        self.assertEqual(200, response.status_code)
        self.assertEqual(1, Client.query.count())
        self.assertEqual(8, Event.query.count())
        self.assert_twilio_response(
            "Thank you for your feedback!",
            response.data,
        )
        client = Client.query.first()
        self.assert_event(client.id, EventType.FEEDBACK_RECEIVED, feedback="foobar")
        self.assertEqual("97204", client.zipcode.zipcode)
        self.assertEqual(alerts_disabled_at, client.alerts_disabled_at)

        self.clock.advance()
        response = self.client.post(
            "/sms/en", data={"Body": "Y", "From": "+12222222222"}
        )
        self.assertEqual(200, response.status_code)
        self.assertEqual(1, Client.query.count())
        self.assertEqual(9, Event.query.count())
        self.assert_twilio_response(
            "Got it! We'll send you timely alerts when air quality in 97204 changes category.",
            response.data,
        )

        client = Client.query.first()
        self.assertEqual("97204", client.zipcode.zipcode)
        self.assertEqual(0, client.alerts_disabled_at)
        self.assert_event(client.id, EventType.RESUBSCRIBE, zipcode="97204")

        alerts_disabled_at = self.clock.advance().timestamp()
        response = self.client.post(
            "/sms/en", data={"Body": "6", "From": "+12222222222"}
        )
        self.assertEqual(200, response.status_code)
        self.assertEqual(1, Client.query.count())
        self.assertEqual(10, Event.query.count())
        self.assert_twilio_response(
            "Got it! You will not receive air quality updates until you text a new zipcode.\n"
            "\n"
            "Tell us why you're leaving so we can improve our service:\n"
            "A. Air quality is not a concern in my area\n"
            "B. SMS texts are not my preferred information source\n"
            "C. Alerts are too frequent\n"
            "D. Information is inaccurate\n"
            "E. Other",
            response.data,
        )

        client = Client.query.first()
        self.assert_event(client.id, EventType.UNSUBSCRIBE, zipcode="97204")
        self.assertEqual("97204", client.zipcode.zipcode)
        self.assertEqual(alerts_disabled_at, client.alerts_disabled_at)

    def test_feedback(self):
        # Give feedback before feedback begin command
        response = self.client.post(
            "/sms/en", data={"Body": "Blah Blah Blah", "From": "+13333333333"}
        )
        client_id = Client.query.filter_by(identifier="+13333333333").first().id

        self.assertEqual(200, response.status_code)
        self.assertEqual(1, Client.query.count())
        self.assertEqual(0, Event.query.count())
        self.assert_twilio_response(
            'Unrecognized option "Blah Blah Blah". Reply with M for the menu.',
            response.data,
        )

        # Go through feedback flow
        self.clock.advance()
        response = self.client.post(
            "/sms/en", data={"Body": "5", "From": "+13333333333"}
        )
        self.assertEqual(200, response.status_code)
        self.assertEqual(1, Client.query.count())
        self.assertEqual(1, Event.query.count())
        self.assert_twilio_response(
            "Please enter your feedback below:",
            response.data,
        )
        self.assert_event(client_id, EventType.FEEDBACK_BEGIN)

        self.clock.advance()
        response = self.client.post(
            "/sms/en", data={"Body": "Blah Blah Blah", "From": "+13333333333"}
        )
        self.assertEqual(200, response.status_code)
        self.assertEqual(1, Client.query.count())
        self.assertEqual(2, Event.query.count())
        self.assert_twilio_response("Thank you for your feedback!", response.data)
        self.assert_event(
            client_id, EventType.FEEDBACK_RECEIVED, feedback="Blah Blah Blah"
        )

        # try to post feedback again
        self.clock.advance()
        response = self.client.post(
            "/sms/en", data={"Body": "Blah Blah Blah", "From": "+13333333333"}
        )
        self.assertEqual(200, response.status_code)
        self.assertEqual(1, Client.query.count())
        self.assertEqual(2, Event.query.count())
        self.assert_twilio_response(
            'Unrecognized option "Blah Blah Blah". Reply with M for the menu.',
            response.data,
        )

        # Now give feedback again
        self.clock.advance()
        response = self.client.post(
            "/sms/en", data={"Body": "5", "From": "+13333333333"}
        )
        self.assertEqual(200, response.status_code)
        self.assertEqual(1, Client.query.count())
        self.assertEqual(3, Event.query.count())
        self.assert_twilio_response(
            "Please enter your feedback below:",
            response.data,
        )
        self.assert_event(client_id, EventType.FEEDBACK_BEGIN)

        # Use a custom option. This shouldn't work because we're not coming from the
        # unsubscribe flow.
        self.clock.advance()
        response = self.client.post(
            "/sms/en", data={"Body": "A", "From": "+13333333333"}
        )
        self.assertEqual(200, response.status_code)
        self.assertEqual(1, Client.query.count())
        self.assertEqual(4, Event.query.count())
        self.assert_twilio_response("Thank you for your feedback!", response.data)
        self.assert_event(client_id, EventType.FEEDBACK_RECEIVED, feedback="A")

    def test_translations(self):
        response = self.client.post(
            "/sms/en", data={"Body": "Blah Blah Blah", "From": "+13333333333"}
        )
        client = Client.query.filter_by(identifier="+13333333333").first()
        self.assertEqual("en", client.locale)

        response = self.client.post(
            "/sms/es", data={"Body": "97204", "From": "+13333333333"}
        )
        self.assertEqual(200, response.status_code)
        self.assertEqual(1, Client.query.count())
        self.assertEqual(1, Event.query.count())
        self.assert_twilio_response(
            "&#161;Bienvenido a Hazebot! Le enviaremos avisos cuando la calidad del aire en Portland 97204 cambie de categor&#237;a. La calidad del aire ahora es BUENO (AQI 42).\n"
            "\n"
            'Guardar este contacto y enviarnos un mensaje de texto con su c&#243;digo postal cuando desee una actualizaci&#243;n instant&#225;nea. Y siempre puede enviar un mensaje de texto con "M" para ver el men&#250; completo.',
            response.data,
            media="localhost:8080/public/vcard/es.vcf",
        )

        client = Client.query.filter_by(identifier="+13333333333").first()
        self.assertEqual("es", client.locale)

    def test_list_prefs(self):
        response = self.client.post(
            "/sms/en", data={"Body": "3", "From": "+13333333333"}
        )
        client_id = Client.query.filter_by(identifier="+13333333333").first().id
        self.assertEqual(200, response.status_code)
        self.assert_twilio_response(
            "Which preference do you want to set?\n"
            "A - Alert Frequency: By default, Hazebot sends alerts at most every 2 hours.\n"
            "B - Alert Threshold: AQI category below which Hazebot won't send alerts.\n"
            "For example, if you set this to MODERATE, "
            "Hazebot won't send alerts when AQI transitions from GOOD to MODERATE or from MODERATE to GOOD.\n"
            "C - Conversion Factor: Conversion factor to use when calculating AQI. For more details, see https://www2.purpleair.com/community/faq#hc-should-i-use-the-conversion-factors-on-the-purpleair-map-1.",
            response.data,
        )
        self.assertEqual(1, Event.query.count())
        self.assert_event(client_id, EventType.LIST_PREFS)

    def test_set_alerting_frequency(self):
        response = self.client.post(
            "/sms/en", data={"Body": "3", "From": "+13333333333"}
        )
        self.assertEqual(200, response.status_code)

        default_frequency = Client.alert_frequency.default
        client = Client.query.filter_by(identifier="+13333333333").first()
        client_id = client.id
        self.assertEqual(default_frequency, client.alert_frequency)

        self.clock.advance()
        response = self.client.post(
            "/sms/en", data={"Body": "A", "From": "+13333333333"}
        )
        self.assertEqual(200, response.status_code)
        self.assert_twilio_response(
            f"Enter an integer between 0 and 24.\n" f"Current: {default_frequency}",
            response.data,
        )
        self.assertEqual(2, Event.query.count())
        self.assert_event(
            client_id, EventType.SET_PREF_REQUEST, pref_name=Client.alert_frequency.name
        )

        new_frequency = 4
        self.clock.advance()
        response = self.client.post(
            "/sms/en", data={"Body": str(new_frequency), "From": "+13333333333"}
        )
        self.assertEqual(200, response.status_code)
        self.assert_twilio_response(
            f"Your Alert Frequency is now {new_frequency}", response.data
        )
        self.assertEqual(3, Event.query.count())
        self.assert_event(
            client_id,
            EventType.SET_PREF,
            pref_name=Client.alert_frequency.name,
            pref_value=new_frequency,
        )
        client = Client.query.filter_by(identifier="+13333333333").first()
        self.assertEqual(new_frequency, client.alert_frequency)

        self.clock.advance()
        response = self.client.post(
            "/sms/en", data={"Body": "3", "From": "+13333333333"}
        )
        self.assertEqual(200, response.status_code)

        self.clock.advance()
        response = self.client.post(
            "/sms/en", data={"Body": "A", "From": "+13333333333"}
        )
        self.assertEqual(200, response.status_code)
        self.assert_twilio_response(
            f"Enter an integer between 0 and 24.\n" f"Current: {new_frequency}",
            response.data,
        )

    def test_set_alerting_threshold(self):
        response = self.client.post(
            "/sms/en", data={"Body": "3", "From": "+13333333333"}
        )
        self.assertEqual(200, response.status_code)

        default_threshold = Client.alert_threshold.default
        default_pm25 = Pm25(default_threshold)
        client = Client.query.filter_by(identifier="+13333333333").first()
        client_id = client.id
        self.assertEqual(default_threshold, client.alert_threshold)

        self.clock.advance()
        response = self.client.post(
            "/sms/en", data={"Body": "B", "From": "+13333333333"}
        )
        self.assertEqual(200, response.status_code)
        self.assert_twilio_response(
            f"Select one of\n"
            f"A - GOOD\n"
            f"B - MODERATE\n"
            f"C - UNHEALTHY FOR SENSITIVE GROUPS\n"
            f"D - UNHEALTHY\n"
            f"E - VERY UNHEALTHY\n"
            f"F - HAZARDOUS\n"
            f"Current: {default_pm25.display}",
            response.data,
        )
        self.assertEqual(2, Event.query.count())
        self.assert_event(
            client_id, EventType.SET_PREF_REQUEST, pref_name=Client.alert_threshold.name
        )

        new_pm25 = Pm25.UNHEALTHY_FOR_SENSITIVE_GROUPS
        self.clock.advance()
        response = self.client.post(
            "/sms/en",
            data={"Body": "C", "From": "+13333333333"},
        )
        self.assertEqual(200, response.status_code)
        self.assert_twilio_response(
            f"Your Alert Threshold is now {new_pm25.display}", response.data
        )
        self.assertEqual(3, Event.query.count())
        self.assert_event(
            client_id,
            EventType.SET_PREF,
            pref_name=Client.alert_threshold.name,
            pref_value=new_pm25.value,
        )
        client = Client.query.filter_by(identifier="+13333333333").first()
        self.assertEqual(new_pm25.value, client.alert_threshold)

        self.clock.advance()
        response = self.client.post(
            "/sms/en", data={"Body": "3", "From": "+13333333333"}
        )
        self.assertEqual(200, response.status_code)

        self.clock.advance()
        response = self.client.post(
            "/sms/en", data={"Body": "B", "From": "+13333333333"}
        )
        self.assertEqual(200, response.status_code)
        self.assert_twilio_response(
            f"Select one of\n"
            f"A - GOOD\n"
            f"B - MODERATE\n"
            f"C - UNHEALTHY FOR SENSITIVE GROUPS\n"
            f"D - UNHEALTHY\n"
            f"E - VERY UNHEALTHY\n"
            f"F - HAZARDOUS\n"
            f"Current: {new_pm25.display}",
            response.data,
        )

    def test_solicit_feedback(self):
        client_id = self._create_client().id
        self.assertEqual(1, Event.query.count())

        bulk_send("Asking for feedback?", self.clock.now().timestamp() + 1, "en", True, True)
        self.assert_event(client_id, EventType.FEEDBACK_REQUEST)
        self.assertEqual(2, Event.query.count())

        self.clock.advance()
        response = self.client.post(
            "/sms/en", data={"Body": "This is some feedback", "From": "+13333333333"}
        )
        self.assertEqual(200, response.status_code)
        self.assert_event(
            client_id, EventType.FEEDBACK_RECEIVED, feedback="This is some feedback"
        )
        self.assertEqual(3, Event.query.count())

        self.clock.advance()
        response = self.client.post(
            "/sms/en", data={"Body": "This is some feedback", "From": "+13333333333"}
        )
        self.assertEqual(200, response.status_code)
        self.assert_twilio_response(
            'Unrecognized option "This is some feedback". Reply with M for the menu or U to stop this alert.',
            response.data,
        )
        self.assertEqual(3, Event.query.count())

    def test_solicit_feedback_with_interleaved_events(self):
        client_id = self._create_client().id
        self.assertEqual(1, Event.query.count())

        bulk_send("Asking for feedback?", self.clock.now().timestamp() + 1, "en", True, True)
        self.assert_event(client_id, EventType.FEEDBACK_REQUEST)
        self.assertEqual(2, Event.query.count())

        self.clock.advance()
        response = self.client.post(
            "/sms/en", data={"Body": "2", "From": "+13333333333"}
        )
        self.assertEqual(200, response.status_code)
        self.assert_any_event(client_id, EventType.LAST)
        self.assertEqual(3, Event.query.count())

        self.clock.advance()
        response = self.client.post(
            "/sms/en", data={"Body": "3", "From": "+13333333333"}
        )
        self.assertEqual(200, response.status_code)
        self.assert_event(client_id, EventType.LIST_PREFS)
        self.assertEqual(4, Event.query.count())

        self.clock.advance()
        response = self.client.post(
            "/sms/en", data={"Body": "B", "From": "+13333333333"}
        )
        self.assertEqual(200, response.status_code)
        self.assert_any_event(client_id, EventType.SET_PREF_REQUEST)
        self.assertEqual(5, Event.query.count())

        self.clock.advance()
        response = self.client.post(
            "/sms/en", data={"Body": "B", "From": "+13333333333"}
        )
        self.assertEqual(200, response.status_code)
        self.assert_any_event(client_id, EventType.SET_PREF)
        self.assertEqual(6, Event.query.count())

        self.clock.advance()
        response = self.client.post(
            "/sms/en", data={"Body": "This is some feedback", "From": "+13333333333"}
        )
        self.assertEqual(200, response.status_code)
        self.assert_event(
            client_id, EventType.FEEDBACK_RECEIVED, feedback="This is some feedback"
        )
        self.assertEqual(7, Event.query.count())

        self.clock.advance()
        response = self.client.post(
            "/sms/en", data={"Body": "This is some feedback", "From": "+13333333333"}
        )
        self.assertEqual(200, response.status_code)
        self.assert_twilio_response(
            'Unrecognized option "This is some feedback". Reply with M for the menu or U to stop this alert.',
            response.data,
        )
        self.assertEqual(7, Event.query.count())

    def test_solicit_feedback_beyond_window(self):
        client_id = self._create_client().id
        self.assertEqual(1, Event.query.count())

        bulk_send("Asking for feedback?", self.clock.now().timestamp() + 1, "en", True, True)
        self.assert_event(client_id, EventType.FEEDBACK_REQUEST)
        self.assertEqual(2, Event.query.count())

        self.clock.advance()
        response = self.client.post(
            "/sms/en", data={"Body": "2", "From": "+13333333333"}
        )
        self.assertEqual(200, response.status_code)
        self.assert_any_event(client_id, EventType.LAST)
        self.assertEqual(3, Event.query.count())

        self.clock.advance(amount=4 * 24 * 60 * 60 - 1)
        response = self.client.post(
            "/sms/en", data={"Body": "This is some feedback", "From": "+13333333333"}
        )
        self.assertEqual(200, response.status_code)
        self.assertEqual(3, Event.query.count())
