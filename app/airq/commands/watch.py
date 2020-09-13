import typing

from airq.commands.base import ApiCommandHandler
from airq.models.subscriptions import Subscription
from airq.models.zipcodes import Zipcode


class WatchHandler(ApiCommandHandler):
    def handle(self, zipcode: typing.Optional[str] = None) -> typing.List[str]:
        if not zipcode:
            zipcode_obj = self.client.get_last_requested_zipcode()
            if not zipcode_obj:
                return [
                    "Looks like you haven't use hazebot before! Please text us a zipcode and we'll send you the air quality"
                ]
        else:
            zipcode_obj = Zipcode.get_by_zipcode(zipcode)
            if not zipcode_obj:
                return [
                    f'Sorry, we can\'t watch "{zipcode}". Please enter a valid zipcode.'
                ]

        subscription, was_created = Subscription.get_or_create(
            self.client.id, zipcode_obj.id
        )

        if not was_created and subscription.is_enabled:
            return [f"Looks like you're already watching {zipcode_obj.zipcode}!"]

        if not subscription.is_enabled:
            subscription.enable()

        return [
            f"You're now watching {zipcode_obj.zipcode}. We'll send you alerts at most once per hour."
        ]
