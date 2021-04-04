import datetime
import pytz
import typing

from unittest import mock
from twilio.base.exceptions import TwilioRestException

from airq.lib.readings import ConversionStrategy
from airq.lib.readings import Pm25
from airq.lib.twilio import TwilioErrorCode
from airq.models.clients import Client
from airq.models.clients import ClientIdentifierType
from airq.models.events import Event
from airq.models.events import EventType
from airq.models.zipcodes import Zipcode
from tests.base import BaseTestCase


class ClientTestCase(BaseTestCase):
    zipcode: typing.Optional[Zipcode] = None

    def setUp(self) -> None:
        super().setUp()
        self.zipcode = Zipcode.query.filter_by(zipcode="97204").first()
        assert self.zipcode is not None, "Mypy is unhappy"
        self._zipcode_pm25 = self.zipcode.pm25

    def tearDown(self) -> None:
        super().tearDown()
        assert self.zipcode is not None, "Mypy is unahppy"
        self.zipcode.pm25 = self._zipcode_pm25
        self.db.session.commit()

    def _make_client(
        self,
        last_activity_at: int = 0,
        last_alert_sent_at: int = 0,
        last_pm25: float = 0.0,
        last_pm_cf_1: float = 0.0,
        last_humidity: float = 0.0,
        alerts_disabled_at: int = 0,
        num_alerts_sent: int = 0,
        created_at: typing.Optional[datetime.datetime] = None,
    ) -> Client:
        assert self.zipcode is not None, "Zipcode not set"
        client = Client(
            identifier="+12222222222",
            type_code=ClientIdentifierType.PHONE_NUMBER,
            last_activity_at=last_activity_at,
            zipcode_id=self.zipcode.id,
            last_alert_sent_at=last_alert_sent_at,
            last_pm25=last_pm25,
            last_pm_cf_1=last_pm_cf_1,
            last_humidity=last_humidity,
            alerts_disabled_at=alerts_disabled_at,
            num_alerts_sent=num_alerts_sent,
            created_at=created_at or self.clock.now(),
        )
        self.db.session.add(client)
        self.db.session.commit()
        return client

    def test_maybe_notify(self):
        zipcode = self.zipcode
        assert zipcode is not None, "Mypy is unhappy"
        zipcode.pm25 = 11
        self.db.session.commit()

        last_pm25 = zipcode.pm25
        client = self._make_client(last_pm25=last_pm25)
        client.alert_threshold = Pm25.GOOD.value
        self.db.session.commit()

        self.assertFalse(client.maybe_notify())
        self.assertEqual(0, client.num_alerts_sent)
        self.assertEqual(0, client.last_alert_sent_at)
        self.assertEqual(0, Event.query.count())

        # Don't notify if before 8 AM
        with mock.patch(
            "airq.models.clients.timestamp",
            return_value=datetime.datetime.fromtimestamp(self.timestamp)
            .replace(hour=7, minute=59, tzinfo=pytz.timezone("America/Los_Angeles"))
            .timestamp(),
        ):
            self.assertFalse(client.maybe_notify())
        self.assertEqual(0, client.num_alerts_sent)
        self.assertEqual(0, client.last_alert_sent_at)
        self.assertEqual(0, Event.query.count())

        # Don't notify if after 9 PM
        with mock.patch(
            "airq.models.clients.timestamp",
            return_value=datetime.datetime.fromtimestamp(self.timestamp)
            .replace(hour=21, minute=0, tzinfo=pytz.timezone("America/Los_Angeles"))
            .timestamp(),
        ):
            self.assertFalse(client.maybe_notify())
        self.assertEqual(0, client.num_alerts_sent)
        self.assertEqual(0, client.last_alert_sent_at)
        self.assertEqual(0, Event.query.count())

        zipcode.pm25 += 2  # tips us over into moderate
        self.db.session.commit()
        self.assertTrue(client.maybe_notify())
        self.assertEqual(1, client.num_alerts_sent)
        self.assertEqual(self.timestamp, client.last_alert_sent_at)
        self.assert_event(
            client.id,
            EventType.ALERT,
            zipcode=zipcode.zipcode,
            pm25=self.zipcode.pm25,
        )

        # Do not resend if the default frequnecy hasn't elapsed
        self.clock.now().timestamp()
        self.clock.advance()
        self.assertFalse(client.maybe_notify())
        self.assertEqual(1, client.num_alerts_sent)

        # Do not resend if the default frequency has elapsed but AQI levels haven't changed
        default_frequency = Client.alert_frequency.default
        self.clock.advance(default_frequency * 60 * 60).timestamp()
        self.assertFalse(client.maybe_notify())
        self.assertEqual(1, client.num_alerts_sent)

        # Do not resend if the default frequency has passed but AQI levels have changed by under 20 points
        zipcode.pm25 -= 2
        self.db.session.commit()
        self.assertGreater(20, abs(client.get_last_aqi() - client.get_current_aqi()))
        self.assertFalse(client.maybe_notify())
        self.assertEqual(1, client.num_alerts_sent)

        # Resend if 6 hours have passed, even if AQI hasn't changed much
        self.clock.advance(60 * 60 * 6 + 1)
        with mock.patch.object(Client, "is_in_send_window", return_value=True):
            self.assertTrue(client.maybe_notify())
        self.assertEqual(2, client.num_alerts_sent)
        self.assertEqual(self.timestamp, client.last_alert_sent_at)
        self.assert_event(
            client.id,
            EventType.ALERT,
            zipcode=zipcode.zipcode,
            pm25=zipcode.pm25,
        )

    def test_maybe_notify_with_alerting_threshold_set(self):
        client = self._make_client()
        client.alert_threshold = Pm25.MODERATE.value
        self.db.session.commit()
        zipcode = client.zipcode

        test_cases = (
            (Pm25.MODERATE - 1, Pm25.MODERATE, False),
            (Pm25.MODERATE, Pm25.MODERATE + 1, False),
            (
                Pm25.UNHEALTHY_FOR_SENSITIVE_GROUPS - 1,
                Pm25.UNHEALTHY_FOR_SENSITIVE_GROUPS,
                True,
            ),
            (
                Pm25.UNHEALTHY_FOR_SENSITIVE_GROUPS,
                Pm25.UNHEALTHY_FOR_SENSITIVE_GROUPS - 1,
                True,
            ),
            (Pm25.UNHEALTHY - 1, Pm25.UNHEALTHY, True),
            (Pm25.UNHEALTHY, Pm25.UNHEALTHY - 1, True),
        )

        for last_pm25, curr_pm25, expected_result in test_cases:
            with self.subTest(
                "{} => {}: {}".format(last_pm25, curr_pm25, expected_result)
            ):
                client.last_alert_sent_at = 0
                client.last_pm25 = last_pm25
                zipcode.pm25 = curr_pm25
                self.db.session.commit()
                self.assertEqual(expected_result, client.maybe_notify())

    def test_filter_eligible_for_sending(self):
        # Don't send if alerts are disabled
        client = self._make_client(alerts_disabled_at=self.timestamp)
        self.db.session.commit()
        self.assertEqual(0, Client.query.filter_eligible_for_sending().count())

        # Don't send if client has no zipcode
        client.alerts_disabled_at = 0
        client.zipcode_id = None
        self.db.session.commit()
        self.assertEqual(0, Client.query.filter_eligible_for_sending().count())

    def test_enable_alerts(self):
        client = self._make_client(alerts_disabled_at=self.timestamp)
        client.enable_alerts()
        self.assertEqual(0, client.alerts_disabled_at)
        self.assert_event(
            client.id, EventType.RESUBSCRIBE, zipcode=client.zipcode.zipcode
        )
        self.assertTrue(client.is_enabled_for_alerts)

    def test_disable_alerts(self):
        client = self._make_client(last_pm25=self.zipcode.pm25)
        client.disable_alerts()
        self.assertEqual(self.timestamp, client.alerts_disabled_at)
        self.assertEqual(9.875, client.last_pm25)
        self.assert_event(
            client.id, EventType.UNSUBSCRIBE, zipcode=client.zipcode.zipcode
        )

    def test_update_subscription(self):
        client = self._make_client(last_pm25=self.zipcode.pm25)
        self.assertEqual(self.zipcode.id, client.zipcode_id)
        self.assertEqual(self.zipcode.pm25, client.last_pm25)

        other = Zipcode.query.filter_by(zipcode="97038").first()
        client.update_subscription(other)
        self.assertEqual(other.id, client.zipcode_id)
        self.assertEqual(other.pm25, client.last_pm25)

    def test_send_message_raises_known_error_code(self):
        client = self._make_client()
        self.assertTrue(client.is_enabled_for_alerts)
        self.assertEqual(0, Event.query.count())
        with mock.patch(
            "airq.models.clients.send_sms",
            side_effect=TwilioRestException(
                "", "", code=TwilioErrorCode.OUT_OF_REGION.value
            ),
        ):
            client.send_message("testing")
        client = Client.query.get(client.id)
        self.assertFalse(client.is_enabled_for_alerts)
        self.assert_event(
            client.id, EventType.UNSUBSCRIBE_AUTO, zipcode=client.zipcode.zipcode
        )

    def test_send_message_raises_unknown_error_code(self):
        client = self._make_client()
        self.assertTrue(client.is_enabled_for_alerts)
        self.assertEqual(0, Event.query.count())
        with mock.patch(
            "airq.models.clients.send_sms",
            side_effect=TwilioRestException("", "", code=77),
        ):
            with self.assertRaises(Exception):
                client.send_message("testing")
        client = Client.query.get(client.id)
        self.assertTrue(client.is_enabled_for_alerts)
        self.assertEqual(0, Event.query.count())

    def test_filter_eligible_for_share_requests(self):
        client = self._make_client(
            last_alert_sent_at=self.clock.now().timestamp() - 60 * 15,
            created_at=self.clock.now() - datetime.timedelta(days=7, seconds=1),
        )
        self.assertEqual(0, Client.query.filter_eligible_for_share_requests().count())

        client.last_alert_sent_at += 1
        self.db.session.commit()
        self.assertEqual(1, Client.query.filter_eligible_for_share_requests().count())

        client.created_at += datetime.timedelta(seconds=1)
        self.db.session.commit()
        self.assertEqual(0, Client.query.filter_eligible_for_share_requests().count())

        client.created_at -= datetime.timedelta(seconds=1)
        client.last_alert_sent_at += 60 * 10 - 1
        self.db.session.commit()
        self.assertEqual(0, Client.query.filter_eligible_for_share_requests().count())

        client.last_alert_sent_at -= 1
        self.db.session.commit()
        self.assertEqual(1, Client.query.filter_eligible_for_share_requests().count())

        event = Event.query.create(client.id, EventType.SHARE_REQUEST)
        self.assertEqual(0, Client.query.filter_eligible_for_share_requests().count())

        event.timestamp -= datetime.timedelta(days=60)
        self.db.session.commit()
        self.assertEqual(1, Client.query.filter_eligible_for_share_requests().count())

        event.timestamp += datetime.timedelta(seconds=2)
        self.db.session.commit()
        self.assertEqual(0, Client.query.filter_eligible_for_share_requests().count())

    def test_request_share(self):
        client = self._make_client(
            last_alert_sent_at=self.clock.now().timestamp() - 60 * 15,
            created_at=self.clock.now() - datetime.timedelta(days=7, seconds=1),
        )
        self.assertFalse(client.request_share())
        self.assertEqual(0, Event.query.count())

        client.last_alert_sent_at += 1
        self.db.session.commit()
        self.assertTrue(client.request_share())
        self.assertEqual(1, Event.query.count())
        self.assert_event(client.id, EventType.SHARE_REQUEST)

        self.assertFalse(client.request_share())
        self.assertEqual(1, Event.query.count())

        share_request = client.get_last_share_request()
        share_request.timestamp -= datetime.timedelta(days=60)
        self.db.session.commit()
        self.assertFalse(client.request_share())
        self.assertEqual(1, Event.query.count())

        share_request.timestamp -= datetime.timedelta(seconds=1)
        self.db.session.commit()
        self.assertTrue(client.request_share())
        self.assertEqual(2, Event.query.count())
        self.assert_event(client.id, EventType.SHARE_REQUEST)
        share_request = client.get_last_share_request()
        self.assertEqual(share_request.timestamp, self.clock.now())
        self.assertEqual(
            2, Event.query.filter_by(type_code=EventType.SHARE_REQUEST).count()
        )

        share_request.timestamp -= datetime.timedelta(days=60, seconds=1)
        client.created_at += datetime.timedelta(seconds=1)
        self.db.session.commit()
        self.assertFalse(client.request_share())
        self.assertEqual(2, Event.query.count())

        client.created_at -= datetime.timedelta(seconds=1)
        self.assertTrue(client.request_share())
        self.assertEqual(3, Event.query.count())
        self.assert_event(client.id, EventType.SHARE_REQUEST)
        share_request = client.get_last_share_request()
        self.assertEqual(share_request.timestamp, self.clock.now())
        self.assertEqual(
            3, Event.query.filter_by(type_code=EventType.SHARE_REQUEST).count()
        )

    def test_get_last_client_event(self):
        client = self._make_client()
        self.assertIsNone(client.get_last_client_event())

        client.log_event(
            EventType.ALERT, zipcode=client.zipcode.zipcode, pm25=client.zipcode.pm25
        )
        self.assertIsNone(client.get_last_client_event())

        client.log_event(EventType.MENU)
        last_event = client.get_last_client_event()
        self.assertEqual(EventType.MENU, last_event.type_code)

        client.log_event(EventType.SHARE_REQUEST)
        last_event = client.get_last_client_event()
        self.assertEqual(EventType.MENU, last_event.type_code)

    def test_alert_frequency(self):
        client = self._make_client()
        self.assertEqual(6, client.alert_frequency)

        client.alert_frequency = 4
        self.db.session.commit()

        client = Client.query.get(client.id)
        self.assertEqual(4, client.alert_frequency)

    def test_alert_threshold(self):
        client = self._make_client()
        self.assertEqual(12, client.alert_threshold)

        client.alert_threshold = Pm25.UNHEALTHY_FOR_SENSITIVE_GROUPS.value
        self.db.session.commit()

        client = Client.query.get(client.id)
        self.assertEqual(35, client.alert_threshold)

    def test_conversion_strategy(self):
        client = self._make_client()
        self.assertEqual(ConversionStrategy.NONE, client.conversion_strategy)

        client.conversion_strategy = ConversionStrategy.US_EPA.value
        self.db.session.commit()

        client = Client.query.get(client.id)
        self.assertEqual(ConversionStrategy.US_EPA, client.conversion_strategy)

    def test_get_current_aqi(self):
        client = self._make_client()
        zipcode = client.zipcode
        self.assertEqual(
            client.get_current_aqi(), zipcode.get_aqi(ConversionStrategy.NONE)
        )

        client.conversion_strategy = ConversionStrategy.US_EPA.value
        self.assertEqual(
            client.get_current_aqi(), zipcode.get_aqi(ConversionStrategy.US_EPA)
        )

    def test_get_current_pm25(self):
        client = self._make_client()
        zipcode = client.zipcode
        self.assertEqual(
            client.get_current_pm25(), zipcode.get_pm25(ConversionStrategy.NONE)
        )

        client.conversion_strategy = ConversionStrategy.US_EPA.value
        self.assertEqual(
            client.get_current_pm25(), zipcode.get_pm25(ConversionStrategy.US_EPA)
        )

    def test_get_current_pm25_level(self):
        client = self._make_client()
        zipcode = client.zipcode
        self.assertEqual(
            client.get_current_pm25_level(),
            zipcode.get_pm25_level(ConversionStrategy.NONE),
        )

        client.conversion_strategy = ConversionStrategy.US_EPA.value
        self.assertEqual(
            client.get_current_pm25_level(),
            zipcode.get_pm25_level(ConversionStrategy.US_EPA),
        )

    def test_get_last_aqi(self):
        client = self._make_client(last_pm25=23.4, last_humidity=28, last_pm_cf_1=18.34)
        self.assertEqual(
            client.get_last_aqi(),
            client.get_last_readings().get_aqi(ConversionStrategy.NONE),
        )

        client.conversion_strategy = ConversionStrategy.US_EPA.value
        self.assertEqual(
            client.get_last_aqi(),
            client.get_last_readings().get_aqi(ConversionStrategy.US_EPA),
        )

    def test_get_last_pm25(self):
        client = self._make_client(last_pm25=23.4, last_humidity=28, last_pm_cf_1=18.34)
        self.assertEqual(
            client.get_last_pm25(),
            client.get_last_readings().get_pm25(ConversionStrategy.NONE),
        )

        client.conversion_strategy = ConversionStrategy.US_EPA.value
        self.assertEqual(
            client.get_last_pm25(),
            client.get_last_readings().get_pm25(ConversionStrategy.US_EPA),
        )

    def test_get_last_pm25_level(self):
        client = self._make_client(last_pm25=23.4, last_humidity=28, last_pm_cf_1=18.34)
        self.assertEqual(
            client.get_last_pm25_level(),
            client.get_last_readings().get_pm25_level(ConversionStrategy.NONE),
        )

        client.conversion_strategy = ConversionStrategy.US_EPA.value
        self.assertEqual(
            client.get_last_pm25_level(),
            client.get_last_readings().get_pm25_level(ConversionStrategy.US_EPA),
        )
