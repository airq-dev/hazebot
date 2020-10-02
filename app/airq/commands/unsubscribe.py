import typing

from airq.commands.base import RegexCommand
from airq.commands.feedback import ReceiveFeedback
from airq.models.zipcodes import Zipcode


class Unsubscribe(RegexCommand):
    pattern = r"^u$"

    def handle(self) -> typing.List[str]:
        if self.client.zipcode is None:
            return self._get_missing_zipcode_message()

        if self.client.alerts_disabled_at:
            return [
                "Looks like you already stopped watching {}.".format(
                    self.client.zipcode.zipcode
                )
            ]

        self.client.disable_alerts()

        message = [
            "Got it! You will not receive air quality updates until you text a new zipcode.",
            "",
            "Tell us why you're leaving so we can improve our service:",
        ]
        for key, choice in ReceiveFeedback.feedback_choices().items():
            message.append(f"{key}. {choice}")
        return message
