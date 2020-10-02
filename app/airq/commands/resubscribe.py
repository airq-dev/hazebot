import typing

from airq.commands.base import RegexCommand
from airq.models.zipcodes import Zipcode


class Resubscribe(RegexCommand):
    pattern = r"^y$"

    def handle(self) -> typing.List[str]:
        if self.client.zipcode is None:
            return self._get_missing_zipcode_message()

        if self.client.is_enabled_for_alerts:
            return [
                "Looks like you're already watching {}.".format(
                    self.client.zipcode.zipcode
                )
            ]

        self.client.enable_alerts()

        return [
            "Got it! We'll send you timely alerts when air quality in {} changes category.".format(
                self.client.zipcode.zipcode
            )
        ]
