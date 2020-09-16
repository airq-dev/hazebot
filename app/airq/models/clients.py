import datetime
import enum
import logging
import typing

from airq.config import db
from airq.lib.twilio import send_sms
from airq.models.requests import Request
from airq.models.zipcodes import Zipcode

if typing.TYPE_CHECKING:
    from airq.models.subscriptions import Subscription


logger = logging.getLogger(__name__)


class ClientIdentifierType(enum.Enum):
    PHONE_NUMBER = 1
    IP = 2


class Client(db.Model):  # type: ignore
    __tablename__ = "clients"

    id = db.Column(db.Integer(), primary_key=True)
    identifier = db.Column(db.String(), nullable=False)
    type_code = db.Column(db.Enum(ClientIdentifierType), nullable=False)
    last_activity_at = db.Column(db.Integer(), nullable=False, index=True, server_default='0')

    zipcode_id = db.Column(db.Integer(), db.ForeignKey('zipcodes.id', name='clients_zipcode_id_fkey'), nullable=True)
    last_pm25 = db.Column(db.Float(), nullable=True)
    last_alert_sent_at = db.Column(db.Integer(), nullable=False, index=True, server_default='0')
    alerts_disabled_at = db.Column(db.Integer(), nullable=False, index=True, server_default='0')
    num_alerts_sent = db.Column(db.Integer(), nullable=False, server_default='0')

    requests = db.relationship("Request")
    zipcode = db.relationship("Zipcode")

    __table_args__ = (
        db.Index(
            "_client_identifier_type_code", "identifier", "type_code", unique=True,
        ),
    )

    @classmethod
    def get_or_create(
        cls, identifier: str, type_code: ClientIdentifierType
    ) -> typing.Tuple["Client", bool]:
        client = cls.query.filter_by(identifier=identifier, type_code=type_code).first()
        if not client:
            client = cls(identifier=identifier, type_code=type_code, last_activity_at=datetime.datetime.now().timestamp())
            db.session.add(client)
            db.session.commit()
            was_created = True
        else:
            was_created = False
        return client, was_created

    def get_last_requested_zipcode(self) -> typing.Optional[Zipcode]:
        return (
            Zipcode.query.join(Request)
            .filter(Request.client_id == self.id)
            .order_by(Request.last_ts.desc())
            .first()
        )

    def log_request(self, zipcode: Zipcode):
        request = Request.query.filter_by(
            client_id=self.id, zipcode_id=zipcode.id,
        ).first()
        now = datetime.datetime.now().timestamp()
        if request is None:
            request = Request(
                client_id=self.id,
                zipcode_id=zipcode.id,
                count=1,
                first_ts=now,
                last_ts=now,
            )
            db.session.add(request)
        else:
            request.count += 1
            request.last_ts = now
        db.session.commit()

    def send_message(self, message: str):
        if self.type_code == ClientIdentifierType.PHONE_NUMBER:
            send_sms(message, self.identifier)
        else:
            # Other clients types don't yet support message sending.
            logger.info("Not messaging client %s: %s", self.id, message)

    def get_subscription(self,) -> typing.Optional["Subscription"]:
        from airq.models.subscriptions import Subscription

        return Subscription.query.filter_by(client_id=self.id, disabled_at=0).first()

    def update_subscription(self, zipcode_id: int, current_pm25: float) -> bool:
        from airq.models.subscriptions import Subscription

        self.last_pm25 = current_pm25
        if self.zipcode_id != zipcode_id:
            self.zipcode_id = zipcode_id
        db.session.commit()

        current_subscription = self.get_subscription()
        if current_subscription:
            if current_subscription.zipcode_id == zipcode_id:
                return False
            current_subscription.disable()

        subscription = Subscription.get_or_create(self.id, zipcode_id)
        if subscription.is_disabled:
            subscription.enable()

        # This is a new subscription
        # Mark it to be checked again in 3 hours.
        subscription.last_pm25 = current_pm25
        subscription.last_executed_at = datetime.datetime.now().timestamp()
        db.session.add(subscription)
        db.session.commit()

        return True

    def mark_seen(self):
        self.last_activity_at = datetime.datetime.now().timestamp()
        db.session.commit()

    def disable_alerts(self):
        self.last_pm25 = None
        self.alerts_disabled_at = datetime.datetime.now().timestamp()
        db.session.commit()
