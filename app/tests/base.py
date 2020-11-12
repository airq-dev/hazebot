import datetime
import pytz
import typing
import unittest
from unittest import mock

from twilio.rest.api.v2010.account.message import MessageList

from airq import models
from airq.config import app
from airq.config import db
from airq.lib.clock import timestamp
from airq.models.events import Event
from airq.models.events import EventType
from tests.mocks.time import MockDateTime


_first_test_case = True


class BaseTestCase(unittest.TestCase):
    app = app
    client = app.test_client()
    db = db
    maxDiff = None

    _persistent_models = (
        models.relations.SensorZipcodeRelation,
        models.sensors.Sensor,
        models.zipcodes.Zipcode,
        models.cities.City,
    )

    # We use duck-typing for some stuff here and I haven't had time to figure out how to type that.
    _patchings = {}  # type: ignore
    _mocks = {}  # type: ignore

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
        global _first_test_case

        super().setUpClass()

        if _first_test_case:
            print("Clearing out ephemeral data")
            cls._truncate_tables(cls._get_ephemeral_models())
            _first_test_case = False

    def run(self, result=None):
        self._setup_mocks()
        return super().run(result=result)

    def tearDown(self):
        super().tearDown()
        self._teardown_mocks()
        self._truncate_tables(self._get_ephemeral_models())

    def _setup_mocks(self):
        self._patchings["clock"] = MockDateTime(
            datetime.datetime(
                year=2020,
                month=9,
                day=18,
                hour=16,
                minute=29,
                second=28,
                tzinfo=pytz.timezone("America/Los_Angeles"),
            )
        )
        self._patchings["send_sms"] = mock.patch.object(MessageList, "create")
        for name, patching in self._patchings.items():
            self._mocks[name] = patching.start()

    def _teardown_mocks(self):
        for patching in self._patchings.values():
            patching.stop()
        self._patchings.clear()
        self._mocks.clear()

    @property
    def clock(self) -> MockDateTime:
        return self._mocks["clock"]

    @property
    def timestamp(self) -> int:
        return timestamp()

    def assert_twilio_response(
        self, expected: str, actual: bytes, media: typing.Optional[str] = None
    ):
        self.assertEqual(
            '<?xml version="1.0" encoding="UTF-8"?>'
            "<Response><Message><Body>"
            "{}"
            "</Body>{}</Message></Response>".format(
                expected, "<Media>{}</Media>".format(media) if media else ""
            ),
            actual.decode(),
        )

    def assert_event(self, client_id: int, event_type: EventType, **data):
        event = (
            Event.query.filter_by(
                client_id=client_id,
                type_code=event_type,
            )
            .order_by(Event.id.desc())
            .first()
        )
        self.assertIsNotNone(event)
        self.assertDictEqual(data, event.data)
