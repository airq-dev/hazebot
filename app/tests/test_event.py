from airq.models.events import Event
from airq.models.events import EventType
from tests.base import BaseTestCase


class EventTestCase(BaseTestCase):
    def test_validate(self):
        test_cases = {
            EventType.QUALITY: {"zipcode": "94119", "pm25": 10.1},
            EventType.DETAILS: {
                "zipcode": "94119",
                "recommendations": ["94118"],
                "pm25": 10.1,
                "num_sensors": 2,
            },
        }

        for event_type, expected_data in test_cases.items():
            with self.subTest(f"{event_type} = {expected_data}"):
                event = Event(
                    client_id=1, type_code=event_type, json_data=expected_data
                )
                data = event.validate()
                self.assertDictEqual(data, expected_data)

    def test_validate_error(self):
        test_cases = {
            EventType.QUALITY: {"zipcode": "94119", "pm25": "turkey"},
            EventType.DETAILS: {
                "zipcode": "94119",
                "recommendations": ["94118"],
                "pm25": 10.1,
                "num_sensors": 2.3,
            },
        }

        for event_type, expected_data in test_cases.items():
            with self.subTest(f"{event_type} = {expected_data}"):
                event = Event(
                    client_id=1, type_code=event_type, json_data=expected_data
                )
                with self.assertRaises(TypeError):
                    event.validate()
