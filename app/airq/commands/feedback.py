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
        message = ["Please text us your feedback:"]  #TODO consider adding cancel option
        self.client.log_event(EventType.FEEDBACK_BEGIN)
        return message


class ReceiveFeedback(SMSCommand):
    def should_handle(self) -> bool:
        return self.client.should_accept_feedback()

    def handle(self) -> typing.List[str]:
        send_email(["info@hazebot.org"], "User gave feedback", self.user_input)
        message = ["Thank you for your feedback!"]
        self.client.log_event(EventType.FEEDBACK_RECEIVED, feedback=self.user_input)
        return message
