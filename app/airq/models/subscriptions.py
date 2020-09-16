import datetime
import pytz
import typing

from sqlalchemy.orm import joinedload

from airq.config import db
from airq.lib.readings import pm25_to_aqi
from airq.lib.readings import Pm25
from airq.lib.twilio import send_sms
from airq.models.clients import Client
from airq.models.clients import ClientIdentifierType
from airq.models.metrics import Metric


class Subscription(db.Model):  # type: ignore
    __tablename__ = "subscriptions"

    # Send alerts at most every one hour to avoid spamming people.
    # One hour seems like a reasonable frequency because AQI
    # doesn't fluctuate very frequently. We should look at implementing
    # logic to smooth out this alerting so that if AQI oscillates
    # between two levels we don't spam the user every hour.
    FREQUENCY = 1 * 60 * 60

    # Send alerts between 8 AM and 9 PM.
    SEND_WINDOW_HOURS = (8, 21)

    zipcode_id = db.Column(
        db.Integer(),
        db.ForeignKey("zipcodes.id", name="subscription_zipcode_id_fkey"),
        nullable=False,
        primary_key=True,
    )
    client_id = db.Column(
        db.Integer(),
        db.ForeignKey("clients.id", name="subscription_client_id_fkey"),
        nullable=False,
        primary_key=True,
    )
    created_at = db.Column(db.Integer(), nullable=False)
    disabled_at = db.Column(db.Integer(), default=0, nullable=False, index=True)
    last_executed_at = db.Column(db.Integer(), default=0, nullable=False, index=True)
    last_pm25 = db.Column(db.Float(), nullable=True)

    client = db.relationship("Client")
    zipcode = db.relationship("Zipcode")

    def __repr__(self) -> str:
        return f"<Subscription {self.zipcode_id} {self.client_id}>"

    @property
    def is_enabled(self) -> bool:
        return not self.is_disabled

    @property
    def is_disabled(self) -> bool:
        return bool(self.disabled_at)

    def enable(self):
        self.disabled_at = 0
        db.session.commit()

    def disable(self):
        # Wipe last_pm25 so when this comes back online we don't hold onto
        # a value from potentially months ago.
        self.client.disable_alerts()
        self.last_pm25 = None
        self.disabled_at = datetime.datetime.now().timestamp()
        db.session.commit()

    @classmethod
    def get_eligible_for_sending(cls) -> typing.List["Subscription"]:
        curr_time = datetime.datetime.now().timestamp()
        cutoff = curr_time - cls.FREQUENCY
        return (
            cls.query.options(joinedload(Subscription.zipcode))
            .join(Client)
            # .filter(Client.type_code == ClientIdentifierType.PHONE_NUMBER)
            .filter(cls.disabled_at == 0)
            # .filter(cls.last_executed_at < cutoff)
            .all()
        )

    @classmethod
    def get_or_create(cls, client_id: int, zipcode_id: int) -> "Subscription":
        subscription = cls.query.filter_by(
            client_id=client_id, zipcode_id=zipcode_id
        ).first()
        if subscription is None:
            subscription = cls(
                client_id=client_id,
                zipcode_id=zipcode_id,
                created_at=datetime.datetime.now().timestamp(),
            )
            db.session.add(subscription)
            db.session.commit()
        return subscription

    @property
    def is_in_send_window(self) -> bool:
        # Timezone can be null since our data is incomplete.
        timezone = self.zipcode.timezone or "America/Los_Angeles"
        dt = datetime.datetime.now(tz=pytz.timezone(timezone))
        send_start, send_end = self.SEND_WINDOW_HOURS
        return send_start <= dt.hour < send_end

    def maybe_notify(self) -> bool:
        # if not self.is_in_send_window:
        #     return False

        metric = (
            Metric.query.filter_by(zipcode_id=self.zipcode_id)
            .order_by(Metric.timestamp.desc())
            .first()
        )
        if not metric:
            return False

        curr_aqi_level = metric.pm25_level
        curr_aqi = metric.aqi

        # Only send if the pm25 changed a level since the last time we sent this alert.
        last_aqi_level = Pm25.from_measurement(self.last_pm25)
        last_aqi = pm25_to_aqi(self.last_pm25)
        # if curr_aqi_level == last_aqi_level:
        #     return False

        message = (
            "Air quality in {city} {zipcode} has changed to {curr_aqi_level} (AQI {curr_aqi})"
        ).format(
            city=self.zipcode.city.name,
            zipcode=self.zipcode.zipcode,
            curr_aqi_level=curr_aqi_level.display,
            curr_aqi=curr_aqi,
        )
        self.client.send_message(message)
        self.client.last_alert_sent_at = datetime.datetime.now().timestamp()
        self.client.last_pm25 = metric.value
        self.client.num_alerts_sent += 1

        self.last_pm25 = metric.value
        self.last_executed_at = self.client.last_alert_sent_at
        db.session.commit()

        return True
