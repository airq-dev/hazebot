from flask_babel import gettext

from airq.commands.base import MessageResponse
from airq.commands.base import RegexCommand
from airq.commands.feedback import ReceiveFeedback


class Unsubscribe(RegexCommand):
    pattern = r"^(6[\.\)]?|u|e|end|unsubscribe)$"

    def handle(self) -> MessageResponse:
        if self.client.zipcode is None:
            return self._get_missing_zipcode_message()

        if self.client.alerts_disabled_at:
            return MessageResponse(
                body=gettext(
                    "Looks like you already stopped watching %(zipcode)s.",
                    zipcode=self.client.zipcode.zipcode,
                )
            )

        self.client.disable_alerts()

        message = [
            gettext(
                "Got it! You will not receive air quality updates until you text a new zipcode."
            ),
            "",
            gettext("Tell us why you're leaving so we can improve our service:"),
        ]
        for key, choice in ReceiveFeedback.feedback_choices():
            message.append(f"{key}. {choice}")
        return MessageResponse.from_strings(message)
