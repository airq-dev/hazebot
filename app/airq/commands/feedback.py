import re
import typing

from airq import config
from airq.commands.base import RegexCommand
from airq.commands.base import SMSCommand
from airq.lib.ses import send_email
from airq.models.clients import Client
from airq.models.events import EventType


class ShowFeedback(RegexCommand):
    pattern = r"^4[\.\)]?$"

    def handle(self) -> typing.List[str]:
        message = ["Please enter your feedback below:"]  # consider adding cancel option
        self.client.log_event(EventType.FEEDBACK_BEGIN)
        return message


class ReceiveFeedback(SMSCommand):
    def should_handle(self) -> bool:
        return self.client.should_accept_feedback()

    def handle(self) -> typing.List[str]:
        feedback = self.user_input
        last_event_type = self.client.get_last_client_event_type()
        if last_event_type == EventType.UNSUBSCRIBE:
            for key, choice in self.feedback_choices().items():
                if re.match(r"^{}[\.\)]?$".format(key), feedback):
                    feedback = choice
                    break

        send_email(
            ["info@hazebot.org"],
            f"User {self.client.identifier} gave feedback",
            f'User feedback: "{feedback}"',
        )
        self.client.log_event(EventType.FEEDBACK_RECEIVED, feedback=feedback)
        return ["Thank you for your feedback!"]

    @staticmethod
    def feedback_choices() -> typing.Dict[str, str]:
        return {
            str(i): choice
            for i, choice in enumerate(
                [
                    "Air quality is not a concern in my area",
                    "SMS texts are not my preferred information source",
                    "Alerts are too frequent",
                    "Information is inaccurate",
                    "Other",
                ],
                start=1,
            )
        }
