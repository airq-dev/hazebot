import re
import typing

from flask_babel import gettext
from werkzeug.utils import cached_property

from airq import config
from airq.commands.base import RegexCommand
from airq.commands.base import SMSCommand
from airq.lib.ses import send_email
from airq.models.clients import Client
from airq.models.events import EventType


class ShowFeedback(RegexCommand):
    pattern = r"^(4[\.\)]?|feedback)$"

    def handle(self) -> typing.List[str]:
        message = ["Please enter your feedback below:"]  # consider adding cancel option
        self.client.log_event(EventType.FEEDBACK_BEGIN)
        return message


class ReceiveFeedback(SMSCommand):
    def should_handle(self) -> bool:
        return self.client.should_accept_feedback()

    def handle(self) -> typing.List[str]:
        selected_choice = self._get_selected_choice()
        if selected_choice == "5":
            return ["Please enter your feedback below:"]

        feedback = self.user_input
        if selected_choice:
            feedback = self.feedback_choices().get(selected_choice, feedback)

        send_email(
            ["info@hazebot.org"],
            "User {} gave feedback{}".format(
                self.client.identifier, " on unsubscribe" if self.is_unsubscribe else ""
            ),
            f'User feedback: "{feedback}"',
        )
        self.client.log_event(EventType.FEEDBACK_RECEIVED, feedback=feedback)
        return ["Thank you for your feedback!"]

    @cached_property
    def is_unsubscribe(self) -> bool:
        return self.client.get_last_client_event_type() == EventType.UNSUBSCRIBE

    def _get_selected_choice(self) -> typing.Optional[str]:
        if self.is_unsubscribe:
            return next(
                (
                    k
                    for k in self.feedback_choices()
                    if re.match(r"^{}[\.\.)]?$".format(k), self.user_input)
                ),
                None,
            )

        return None

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
