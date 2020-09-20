import os

from airq.models.cities import City
from airq.models.relations import SensorZipcodeRelation
from airq.models.sensors import Sensor
from airq.models.zipcodes import Zipcode
from airq.sync import models_sync
from airq.sync.geonames import GEONAMES_URL
from airq.sync.geonames import ZIP_2_TIMEZONES_URL
from airq.sync.purpleair import PURPLEAIR_URL
from tests.base import BaseTestCase
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

        with MockRequests(
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
