import unittest

from airq import config


class BaseTestCase(unittest.TestCase):
    app = config.app
    client = app.test_client()
    db = config.db
