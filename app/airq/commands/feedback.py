import re
import typing

from flask_babel import gettext
from werkzeug.utils import cached_property

from airq.commands.base import MessageResponse
from airq.commands.base import RegexCommand
from airq.commands.base import SMSCommand
from airq.lib.ses import send_email
from airq.models.events import EventType


class ShowFeedback(RegexCommand):
    pattern = r"^(5[\.\)]?|feedback)$"

    def handle(self) -> MessageResponse:
        self.client.log_event(EventType.FEEDBACK_BEGIN)
        # TODO: Consider adding cancel option
        return MessageResponse(body=gettext("Please enter your feedback below:"))


class ReceiveFeedback(SMSCommand):
    def should_handle(self) -> bool:
        return self.client.should_accept_feedback()

    def handle(self) -> MessageResponse:
        selected_choice = self._get_selected_choice()
        if selected_choice == "E":
            return MessageResponse(body=gettext("Please enter your feedback below:"))

        feedback = self.user_input
        if selected_choice:
            feedback = dict(self.feedback_choices()).get(selected_choice, feedback)

        send_email(
            ["info@hazebot.org"],
            "User {} gave feedback{}".format(
                self.client.identifier, " on unsubscribe" if self.is_unsubscribe else ""
            ),
            f'User feedback: "{feedback}"',
        )
        self.client.log_event(EventType.FEEDBACK_RECEIVED, feedback=feedback)
        return MessageResponse(body=gettext("Thank you for your feedback!"))

    @cached_property
    def is_unsubscribe(self) -> bool:
        return self.client.get_last_client_event_type() == EventType.UNSUBSCRIBE

    def _get_selected_choice(self) -> typing.Optional[str]:
        return (
            next(
                (
                    k
                    for k, _ in self.feedback_choices()
                    if re.match(r"^{}[\.\.)]?$".format(k), self.user_input)
                ),
                None,
            )
            if self.is_unsubscribe
            else None
        )

    @staticmethod
    def feedback_choices() -> typing.List[typing.Tuple[str, str]]:
        return [
            ("A", gettext("Air quality is not a concern in my area")),
            ("B", gettext("SMS texts are not my preferred information source")),
            ("C", gettext("Alerts are too frequent")),
            ("D", gettext("Information is inaccurate")),
            ("E", gettext("Other")),
        ]
