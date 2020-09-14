import typing

from airq.commands.base import ApiCommandHandler
from airq.models.subscriptions import Subscription
from airq.models.zipcodes import Zipcode


class StopHandler(ApiCommandHandler):
    def handle(self, stop_all: bool = False) -> typing.List[str]:
        if stop_all:
            subscriptions = Subscription.query.filter_by(
                client_id=self.client.id, disabled_at=0
            ).all()
            if not subscriptions:
                return ["Looks like you don't have any subscriptions to disable."]

            for subscription in subscriptions:
                subscription.disable()

            return [
                f"Got it! You won't recieve air quality alerts for {len(subscriptions)} zipcodes."
            ]

        zipcode = self.client.get_last_requested_zipcode()
        if not zipcode:
            return [
                "Looks like you haven't use hazebot before! Please text us a zipcode and we'll send you the air quality."
            ]

        subscription = Subscription.query.filter_by(
            client_id=self.client.id, zipcode_id=zipcode.id,
        ).first()

        if not subscription or subscription.is_disabled:
            return [f"Looks like you already stopped watching {zipcode.zipcode}."]

        subscription.disable()
        return [
            f"Got it! You will no longer recieve air quality alerts for {zipcode.zipcode}."
        ]
