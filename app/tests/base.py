import datetime
import json
import unittest

from flask_sqlalchemy import SessionBase
from unittest import mock

from airq import config
from airq.lib import datetime as airq_datetime


# Much of the following code is shamelessly ripped from:
# http://koo.fi/blog/2015/10/22/flask-sqlalchemy-and-postgresql-unit-testing-with-transaction-savepoints/
class TestingSession(SessionBase):
    def __init__(self, db, bind, **options):
        self.app = db.get_app()
        super().__init__(autocommit=False, autoflush=True, bind=bind, **options)

    def __call__(self):
        # Flask-SQLAlchemy wants to create a new session
        # Simply return the existing session
        return self

    def get_bind(self, mapper=None, clause=None):
        # mapper is None if someone tries to just get a connection
        if mapper is not None:
            info = getattr(mapper.mapped_table, "info", {})
            bind_key = info.get("bind_key")
            if bind_key is not None:
                state = flask.ext.sqlalchemy.get_state(self.app)
                return state.db.get_engine(self.app, bind=bind_key)
        return super().get_bind(mapper, clause)


class BaseTestCase(unittest.TestCase):
    app = config.app
    client = app.test_client()
    db = config.db
    timestamp = None

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        with open("/home/app/app/tests/fixtures/metadata.json") as f:
            metadata = json.load(f)
        cls.timestamp = metadata["generated_ts"]

    def run(self, result=None, *args):
        with mock.patch.object(
            airq_datetime,
            "now",
            return_value=datetime.datetime.fromtimestamp(self.timestamp),
        ):
            return super().run(result=result)


class BaseAppTestCase(BaseTestCase):
    def setUp(self):
        super().setUp()

        # Create a connection and start a transaction. This is needed so that
        # we can run the drop_all/create_all inside the same transaction as
        # the tests
        connection = self.db.engine.connect()
        transaction = connection.begin()

        session_backup = self.db.session
        self.db.session = TestingSession(self.db, connection)

        self.savepoint = self.db.session.begin_nested()
        self.nested_savepoint = self.db.session.begin_nested()
        self.backup = self.db.session
        self.db.session = self.nested_savepoint.session

        # This is for using app_context().pop()
        self.db.session.remove = lambda: None

    def tearDown(self):
        super().tearDown()

        self.savepoint.rollback()
        self.db.session = self.backup
