import datetime
import pytz
import typing

from sqlalchemy.orm import joinedload

from airq.config import db
from airq.lib.twilio import send_sms
from airq.models.clients import Client
from airq.models.clients import ClientIdentifierType
from airq.models.metrics import Metric


class Subscription(db.Model):  # type: ignore
    __tablename__ = "subscriptions"

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
        self.disabled_at = datetime.datetime.now().timestamp()
        db.session.commit()

    @classmethod
    def get_eligible_for_sending(cls) -> typing.List["Subscription"]:
        curr_time = datetime.datetime.now().timestamp()
        cutoff = curr_time - (60 * 60)
        return (
            cls.query.options(joinedload(Subscription.zipcode))
            .join(Client)
            .filter(Client.type_code == ClientIdentifierType.PHONE_NUMBER)
            .filter(cls.disabled_at == 0)
            .filter(cls.last_executed_at < cutoff)
            .all()
        )

    @classmethod
    def get_or_create(
        cls, client_id: int, zipcode_id: int
    ) -> typing.Tuple["Subscription", bool]:
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
            was_created = True
        else:
            was_created = False
        return subscription, was_created

    @property
    def is_in_send_window(self) -> bool:
        # Timezone can be null since our data is incomplete.
        timezone = self.zipcode.timezone or "America/Los_Angeles"
        dt = datetime.datetime.now(tz=pytz.timezone(timezone))
        return 8 <= dt.hour <= 21

    def maybe_notify(self) -> bool:
        if not self.is_in_send_window:
            return False

        metrics = (
            Metric.query.filter_by(zipcode_id=self.zipcode_id)
            .order_by(Metric.timestamp.desc())
            .limit(2)
            .all()
        )
        if len(metrics) != 2:
            return False

        curr_metrics = metrics[0]
        last_metrics = metrics[1]

        if (
            curr_metrics.pm25_level.is_unhealthy
            and last_metrics.pm25_level.is_unhealthy
        ) or (
            curr_metrics.pm25_level.is_healthy and last_metrics.pm25_level.is_healthy
        ):
            return False

        message = (
            "AQI near {city} {zipcode} is now {curr_aqi_level} ({curr_aqi}) {direction} from {last_aqi_level} ({last_aqi})\n"
            "\n"
            'Reply "s" to stop AQI alerts for {zipcode}'
        ).format(
            city=self.zipcode.city.name,
            zipcode=self.zipcode.zipcode,
            direction="up" if curr_metrics.value > last_metrics.value else "down",
            curr_aqi_level=curr_metrics.pm25_level.display,
            curr_aqi=curr_metrics.value,
            last_aqi_level=last_metrics.pm25_level.display,
            last_aqi=last_metrics.value,
        )
        self.client.send_message(message)

        self.last_executed_at = datetime.datetime.now().timestamp()
        db.session.commit()

        return True
