import datetime
import pytz
import typing
import unittest

from airq import models
from airq.config import app
from airq.config import db
from airq.lib.clock import _clock
from tests.mocks.time import MockDateTime


class BaseTestCase(unittest.TestCase):
    app = app
    db = db
    client = app.test_client()

    _persistent_models = (
        models.relations.SensorZipcodeRelation,
        models.sensors.Sensor,
        models.zipcodes.Zipcode,
        models.cities.City,
    )

    __first_test_case = True

    dt = datetime.datetime(
        year=2020,
        month=9,
        day=18,
        hour=20,
        minute=29,
        second=28,
        tzinfo=pytz.timezone("America/Los_Angeles"),
    )
    timestamp = dt.timestamp()

    @classmethod
    def _get_ephemeral_models(cls):
        ephemeral_models = []
        for c in cls.db.Model._decl_class_registry.values():
            if isinstance(c, type) and issubclass(c, db.Model):
                if c not in cls._persistent_models:
                    ephemeral_models.append(c)
        return ephemeral_models

    @classmethod
    def _truncate_tables(cls, models: typing.Iterable[db.Model]):  # type: ignore
        for model in models:
            stmt = model.__table__.delete()
            cls.db.session.execute(stmt)
            cls.db.session.commit()

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        _clock._impl = MockDateTime(cls.dt)

        if cls.__first_test_case:
            print("Clearing out ephemeral data")
            cls._truncate_tables(cls._get_ephemeral_models())
            cls.__first_test_case = False

    def setUp(self):
        super().setUp()
        self.maxDiff = None

    def tearDown(self):
        super().tearDown()
        self._truncate_tables(self._get_ephemeral_models())

    def assert_twilio_response(self, expected: str, actual: bytes):
        self.assertEqual(
            '<?xml version="1.0" encoding="UTF-8"?>'
            "<Response><Message>"
            "{}"
            "</Message></Response>".format(expected).encode(),
            actual,
        )
