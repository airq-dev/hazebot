from tests.base import BaseAppTestCase


class SMSTestCase(BaseAppTestCase):
    def test_get_zipcode(self):
        response = self.client.post(
            "/sms", data={"Body": "94703", "From": "+12222222222"}
        )
        print(response)
