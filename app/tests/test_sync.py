import json
import os
import requests
import typing
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


class MockResponse:
    def __init__(self, file_path: str):
        self._file_path = file_path

    def __repr__(self) -> str:
        return f"MockResponse({self._file_path})"

    @property
    def _full_path(self) -> str:
        basedir = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(basedir, 'fixtures', self._file_path)

    def raise_for_status(self):
        pass

    def iter_content(self, chunk_size: typing.Optional[int] = None):
        with open(self._full_path, 'rb') as f:
            return [f.read()]

    def json(self) -> dict:
        with open(self._full_path) as f:
            return json.load(f)


class MockRequests:
    def get(self, url, *args, **kwargs) -> MockResponse:
        if url == GEONAMES_URL:
            return MockResponse('geonames/US.zip')
        elif url == ZIP_2_TIMEZONES_URL:
            return MockResponse('geonames/zipcodes_to_timezones.gz')
        elif url == PURPLEAIR_URL:
            return MockResponse('purpleair/purpleair.json')
        raise Exception(f"Cannot find a fixture for {url}")


MOCK_REQUESTS = MockRequests()


class SyncTestCase(BaseTestCase):
    def _truncate_tables(self):
        models_to_delete = [
            SensorZipcodeRelation,
            Sensor,
            Zipcode,
            City
        ]
        for model in models_to_delete:
            stmt = model.__table__.delete()
            self.db.session.execute(stmt)
            self.db.session.commit()
            self.assertEqual(0, model.query.count())

    def test_sync(self):
        self._truncate_tables()

        with mock.patch.object(requests, 'get', MOCK_REQUESTS.get):
            models_sync(force_rebuild_geography=True)

        self.assertEqual(29541, Zipcode.query.count())
        self.assertEqual(40959, Zipcode.query.count())
        self.assertEqual(7079, Sensor.query.count())
        self.assertEqual(113370, SensorZipcodeRelation.query.count())


if __name__ == '__main__':
    unittest.main()