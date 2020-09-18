import argparse
import os
import requests
import unittest
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
from tests.mocks.requests import MockRequests


class SyncTestCase(BaseTestCase):
    def _truncate_tables(self):
        models_to_delete = [SensorZipcodeRelation, Sensor, Zipcode, City]
        for model in models_to_delete:
            stmt = model.__table__.delete()
            self.db.session.execute(stmt)
            self.db.session.commit()
            self.assertEqual(0, model.query.count())

    def test_sync(self):
        skip_force_rebuild = bool(os.getenv("SKIP_FORCE_REBUILD", False))
        if not skip_force_rebuild:
            print("Truncating tables")
            self._truncate_tables()

        with MockRequests({
            GEONAMES_URL: 'geonames/US.zip',
            ZIP_2_TIMEZONES_URL: 'geonames/zipcodes_to_timezones.gz',
            PURPLEAIR_URL: 'purpleair/purpleair.json'
        }):
            models_sync(only_if_empty=skip_force_rebuild, force_rebuild_geography=True)

        self.assertEqual(29541, City.query.count())
        self.assertEqual(40959, Zipcode.query.count())
        self.assertEqual(7084, Sensor.query.count())
        self.assertEqual(113479, SensorZipcodeRelation.query.count())


if __name__ == "__main__":
    unittest.main()
