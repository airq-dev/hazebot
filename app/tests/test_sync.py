import os
import logging
import requests

from requests.exceptions import HTTPError
from unittest import mock

from airq.models.cities import City
from airq.models.relations import SensorZipcodeRelation
from airq.models.sensors import Sensor
from airq.models.zipcodes import Zipcode
from airq.sync import models_sync
from airq.sync.geonames import GEONAMES_URL
from airq.sync.geonames import ZIP_2_TIMEZONES_URL
from airq.sync.purpleair import PURPLEAIR_URL
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
                PURPLEAIR_URL: "purpleair/purpleair.json",
            }
        ):
            models_sync(only_if_empty=skip_force_rebuild, force_rebuild_geography=True)

        self.assertGreater(City.query.count(), 0)
        self.assertGreater(Zipcode.query.count(), 0)
        self.assertGreater(Sensor.query.count(), 0)
        self.assertGreater(SensorZipcodeRelation.query.count(), 0)

    @mock.patch.object(logging.Logger, "exception")
    @mock.patch.object(logging.Logger, "warning")
    def test_sync_error(self, mock_log_warning, mock_log_exception):
        error = HTTPError("foo")
        mock_requests = MockRequests({PURPLEAIR_URL: ErrorResponse(error)})
        with mock_requests:
            models_sync(only_if_empty=False, force_rebuild_geography=False)
        mock_log_warning.assert_called_once_with(
            "%s updating purpleair data: %s",
            "HTTPError",
            error,
            exc_info=True,
        )

        self.clock.advance(60 * 60)
        with mock_requests:
            models_sync(only_if_empty=False, force_rebuild_geography=False)
        mock_log_exception.assert_called_once_with(
            "%s seconds have passed since the last successful sensor sync: %s",
            3600,
            error,
        )
