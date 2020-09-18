import datetime
import unittest
from unittest import mock

from airq import config
from airq.lib import datetime as airq_datetime


class BaseTestCase(unittest.TestCase):
    app = config.app
    client = app.test_client()
    db = config.db

    timestamp = 1600447422

    @mock.patch.object(airq_datetime, 'now', return_value=datetime.datetime.fromtimestamp(timestamp))
    def run(self, result=None, *args):
        return super().run(result=result)


class BaseAppTestCase(BaseTestCase):
    def setUp(self):
        self.savepoint = self.db.session.begin_nested()
        nested_savepoint = self.db.session.begin_nested()
        self.backup = self.db.session
        config.db.session = nested_savepoint.session

    def tearDown(self):
        self.savepoint.rollback()
        self.db.session = self.backup