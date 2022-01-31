import datetime
import os
import logging

from requests.exceptions import HTTPError
from unittest import mock

from airq.config import app
from airq.lib.purpleair import PURPLEAIR_DATA_API_URL
from airq.lib.purpleair import PURPLEAIR_SENSORS_API_URL
from airq.models.cities import City
from airq.models.clients import Client
from airq.models.clients import ClientIdentifierType
from airq.models.relations import SensorZipcodeRelation
from airq.models.sensors import Sensor
from airq.models.zipcodes import Zipcode
from airq.sync import models_sync
from airq.sync.purpleair import _send_share_requests
from airq.sync.geonames import GEONAMES_URL
from airq.sync.geonames import ZIP_2_TIMEZONES_URL
from tests.base import BaseTestCase
from tests.mocks.requests import ErrorResponse
from tests.mocks.requests import MockRequests


class SyncTestCase(BaseTestCase):
    def test_sync(self):
        skip_force_rebuild = bool(os.getenv("SKIP_FORCE_REBUILD", False))
        if not skip_force_rebuild:
            print("Truncating tables")
            self._truncate_tables(self._persistent_models)
            self.assertEqual(City.query.count(), 0)
            self.assertEqual(Zipcode.query.count(), 0)
            self.assertEqual(Sensor.query.count(), 0)
            self.assertEqual(SensorZipcodeRelation.query.count(), 0)

        with MockRequests.for_urls(
            {
                GEONAMES_URL: "geonames/US.zip",
                ZIP_2_TIMEZONES_URL: "geonames/zipcodes_to_timezones.gz",
                PURPLEAIR_DATA_API_URL: "purpleair/pm_cf_1.json",
                PURPLEAIR_SENSORS_API_URL: "purpleair/purpleair.json",
            }
        ):
            models_sync(only_if_empty=skip_force_rebuild, force_rebuild_geography=True)

        self.assertGreater(City.query.count(), 0)
        self.assertGreater(Zipcode.query.count(), 0)
        self.assertGreater(Sensor.query.count(), 0)
        self.assertGreater(SensorZipcodeRelation.query.count(), 0)

        # Assert that zipcodes with a valid pm25 have a metrics_data blob
        zipcodes = Zipcode.query.filter(Zipcode.pm25_updated_at > 0).all()
        self.assertGreater(len(zipcodes), 0)
        for zipcode in zipcodes:
            self.assertIsNotNone(zipcode.metrics_data)
            self.assertTrue(len(zipcode.metrics_data["sensor_ids"]) > 0)

    def test_send_share_requests(self):
        zipcode = Zipcode.query.first()
        client = Client(
            identifier="+12222222222",
            type_code=ClientIdentifierType.PHONE_NUMBER,
            last_activity_at=0,
            zipcode_id=zipcode.id,
            last_alert_sent_at=(self.clock.now().timestamp() - 60 * 15) + 1,
            last_pm25=0.0,
            last_pm_cf_1=0.0,
            last_humidity=0.0,
            alerts_disabled_at=0,
            num_alerts_sent=0,
            created_at=self.clock.now() - datetime.timedelta(days=7, seconds=1),
        )
        self.db.session.add(client)
        self.db.session.commit()

        self.db.session.begin_nested()
        self.assertEqual(_send_share_requests(), 1)
        self.db.session.rollback()

        with self.mock_config(HAZEBOT_SHARE_REQUESTS_ENABLED=False):
            self.assertEqual(_send_share_requests(), 0)

    @mock.patch.object(logging.Logger, "log")
    def test_sync_error(self, mock_log):
        error = HTTPError("foo")
        mock_requests = MockRequests(
            {
                PURPLEAIR_SENSORS_API_URL: ErrorResponse(error),
                PURPLEAIR_DATA_API_URL: ErrorResponse(error),
            }
        )
        with mock_requests:
            models_sync(only_if_empty=False, force_rebuild_geography=False)
        mock_log.assert_any_call(
            logging.WARNING,
            "%s updating purpleair data: %s",
            "HTTPError",
            error,
            exc_info=True,
        )
        mock_log.reset_mock()

        self.clock.advance(60 * 60)
        with mock_requests:
            models_sync(only_if_empty=False, force_rebuild_geography=False)
        mock_log.assert_any_call(
            logging.ERROR,
            "%s updating purpleair data: %s",
            "HTTPError",
            error,
            exc_info=True,
        )
