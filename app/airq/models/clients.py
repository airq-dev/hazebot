import datetime
import enum
import logging
import typing

from flask_sqlalchemy import BaseQuery
from sqlalchemy import and_
from sqlalchemy import func
from sqlalchemy.orm import joinedload
from sqlalchemy.orm import Query
from twilio.base.exceptions import TwilioRestException

from airq.config import db
from airq.lib.clock import now
from airq.lib.clock import timestamp
from airq.lib.readings import Pm25
from airq.lib.readings import pm25_to_aqi
from airq.lib.sms import coerce_phone_number
from airq.lib.twilio import send_sms
from airq.lib.twilio import TwilioErrorCode
from airq.models.events import Event
from airq.models.events import EventType
from airq.models.requests import Request
from airq.models.zipcodes import Zipcode


logger = logging.getLogger(__name__)


class ClientIdentifierType(enum.Enum):
    PHONE_NUMBER = 1
    IP = 2


class ClientQuery(BaseQuery):

    #
    # Fetchers
    #

    def get_or_create(
        self, identifier: str, type_code: ClientIdentifierType
    ) -> typing.Tuple["Client", bool]:
        client = self.filter_by(identifier=identifier, type_code=type_code).first()
        if not client:
            client = Client(
                identifier=identifier, type_code=type_code, last_activity_at=timestamp()
            )
            db.session.add(client)
            db.session.commit()
            was_created = True
        else:
            was_created = False
        return client, was_created

    def get_by_phone_number(self, phone_number: str) -> typing.Optional["Client"]:
        phone_number = coerce_phone_number(phone_number)
        return self.filter_phones().filter_by(identifier=phone_number).first()

    #
    # Filters
    #

    def filter_phones(self) -> "ClientQuery":
        return self.filter(Client.type_code == ClientIdentifierType.PHONE_NUMBER)

    def filter_inactive_since(self, timestamp: float) -> "ClientQuery":
        return (
            self.filter_phones()
            .filter(Client.last_activity_at < timestamp)
            .filter(Client.last_alert_sent_at < timestamp)
        )

    def filter_eligible_for_sending(self) -> "ClientQuery":
        cutoff = timestamp() - Client.FREQUENCY
        return (
            self.filter_phones()
            .options(joinedload(Client.zipcode))
            .filter(Client.alerts_disabled_at == 0)
            .filter(Client.last_alert_sent_at < cutoff)
            .filter(Client.zipcode_id.isnot(None))
        )

    def filter_eligible_for_share_requests(self) -> "ClientQuery":
        subq = (
            Event.query.filter(Event.type_code == EventType.SHARE_REQUEST)
            .filter(Event.timestamp > Client.get_share_request_cutoff())
            .with_entities(Event.client_id, Event.timestamp)
            .subquery()
        )
        share_window_start, share_window_end = Client.get_share_window()
        return (
            self.filter_phones()
            .outerjoin(subq, and_(subq.c.client_id == Client.id))
            .filter(subq.c.timestamp == None)
            # Client must have signed up more than 7 days ago
            .filter(Client.created_at < now() - datetime.timedelta(days=7))
            .filter(Client.last_alert_sent_at > share_window_start)
            .filter(Client.last_alert_sent_at < share_window_end)
        )

    #
    # Stats
    #

    def get_total_num_sends(self) -> int:
        return (
            self.filter_phones()
            .with_entities(func.sum(Client.num_alerts_sent))
            .scalar()
            or 0
        )

    def get_total_new(self) -> int:
        """Number of new clients in the last day"""
        return (
            self.filter_phones()
            .filter(func.timezone("PST", Client.created_at) > now().date())
            .with_entities(func.count(Client.id))
            .scalar()
            or 0
        )

    def get_total_num_subscriptions(self) -> int:
        return (
            self.filter_phones()
            .filter(Client.alerts_disabled_at == 0)
            .filter(Client.zipcode_id.isnot(None))
            .count()
        )

    def get_activity_counts(self):
        windows = [1, 2, 3, 4, 5, 6, 7, 30]
        curr_time = timestamp()
        counts = {window: 0 for window in windows}
        for client in self.filter_phones().all():
            for window in windows:
                ts = curr_time - (window * 24 * 60 * 60)
                if client.last_activity_at > ts or client.last_alert_sent_at > ts:
                    counts[window] += 1
        return counts


class Client(db.Model):  # type: ignore
    __tablename__ = "clients"

    query_class = ClientQuery

    id = db.Column(db.Integer(), primary_key=True)
    identifier = db.Column(db.String(), nullable=False)
    type_code = db.Column(db.Enum(ClientIdentifierType), nullable=False)
    created_at = db.Column(
        db.TIMESTAMP(timezone=True), default=now, index=True, nullable=False
    )
    last_activity_at = db.Column(
        db.Integer(), nullable=False, index=True, server_default="0"
    )

    zipcode_id = db.Column(
        db.Integer(),
        db.ForeignKey("zipcodes.id", name="clients_zipcode_id_fkey"),
        nullable=True,
    )
    last_pm25 = db.Column(db.Float(), nullable=True)
    last_alert_sent_at = db.Column(
        db.Integer(), nullable=False, index=True, server_default="0"
    )
    alerts_disabled_at = db.Column(
        db.Integer(), nullable=False, index=True, server_default="0"
    )
    num_alerts_sent = db.Column(db.Integer(), nullable=False, server_default="0")

    requests = db.relationship("Request")
    zipcode = db.relationship("Zipcode")
    events = db.relationship("Event")

    __table_args__ = (
        db.Index(
            "_client_identifier_type_code",
            "identifier",
            "type_code",
            unique=True,
        ),
    )

    def __repr__(self) -> str:
        return f"<Client {self.identifier}>"

    # Send alerts at most every TWO hours to avoid spamming people.
    # One hour seems like a reasonable frequency because AQI
    # doesn't fluctuate very frequently. We should look at implementing
    # logic to smooth out this alerting so that if AQI oscillates
    # between two levels we don't spam the user every TWO hour.
    # TODO: update logic with hysteresis to avoid spamming + save money
    FREQUENCY = 2 * 60 * 60

    # Send alerts between 8 AM and 9 PM.
    SEND_WINDOW_HOURS = (8, 21)

    # Time alotted between feedback command and feedback response.
    FEEDBACK_RESPONSE_TIME = datetime.timedelta(hours=1)

    @classmethod
    def get_share_window(self) -> typing.Tuple[int, int]:
        ts = timestamp()
        share_window_start = ts - 60 * 15
        share_window_end = ts - 60 * 5
        return share_window_start, share_window_end

    @classmethod
    def get_share_request_cutoff(self) -> datetime.datetime:
        return now() - datetime.timedelta(days=60)

    #
    # Presence
    #

    def log_request(self, zipcode: Zipcode):
        request = Request.query.filter_by(
            client_id=self.id,
            zipcode_id=zipcode.id,
        ).first()
        now = timestamp()
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

    def mark_seen(self):
        self.last_activity_at = timestamp()
        db.session.commit()

    #
    # AQI
    #

    @property
    def last_aqi(self) -> typing.Optional[int]:
        return pm25_to_aqi(self.last_pm25)

    #
    # Alerting
    #

    @property
    def is_enabled_for_alerts(self) -> bool:
        return bool(self.zipcode_id and not self.alerts_disabled_at)

    def update_subscription(self, zipcode: Zipcode) -> bool:
        self.last_pm25 = zipcode.pm25
        curr_zipcode_id = self.zipcode_id
        self.zipcode_id = zipcode.id
        db.session.commit()
        return curr_zipcode_id != self.zipcode_id

    def disable_alerts(self, is_automatic=False):
        if self.alerts_disabled_at == 0:
            self.alerts_disabled_at = timestamp()
            db.session.commit()
            self.log_event(
                EventType.UNSUBSCRIBE_AUTO if is_automatic else EventType.UNSUBSCRIBE,
                zipcode=self.zipcode.zipcode,
            )

    def enable_alerts(self):
        if self.alerts_disabled_at > 0:
            self.last_pm25 = self.zipcode.pm25
            self.alerts_disabled_at = 0
            db.session.commit()
            self.log_event(EventType.RESUBSCRIBE, zipcode=self.zipcode.zipcode)

    @property
    def is_in_send_window(self) -> bool:
        if self.zipcode_id is None:
            return False
        # Timezone can be null since our data is incomplete.
        timezone = self.zipcode.timezone or "America/Los_Angeles"
        dt = now(timezone=timezone)
        send_start, send_end = self.SEND_WINDOW_HOURS
        return send_start <= dt.hour < send_end

    def send_message(self, message: str) -> bool:
        if self.type_code == ClientIdentifierType.PHONE_NUMBER:
            try:
                send_sms(message, self.identifier)
            except TwilioRestException as e:
                code = TwilioErrorCode.from_exc(e)
                if code:
                    logger.warning(
                        "Disabling alerts for recipient %s: %s",
                        self,
                        code.name,
                    )
                    self.disable_alerts(is_automatic=True)
                    return False
                else:
                    raise
        else:
            # Other clients types don't yet support message sending.
            logger.info("Not messaging client %s: %s", self.id, message)

        return True

    def maybe_notify(self) -> bool:
        if not self.is_in_send_window:
            return False

        if self.last_alert_sent_at >= timestamp() - self.FREQUENCY:
            return False

        curr_pm25 = self.zipcode.pm25
        curr_aqi_level = Pm25.from_measurement(curr_pm25)
        curr_aqi = pm25_to_aqi(curr_pm25)

        # Only send if the pm25 changed a level since the last time we sent this alert.
        last_aqi_level = Pm25.from_measurement(self.last_pm25)
        if curr_aqi_level == last_aqi_level:
            return False

        # Do not alert clients who received an alert recently unless AQI has changed markedly.
        was_alerted_recently = self.last_alert_sent_at > timestamp() - (60 * 60 * 6)
        last_aqi = self.last_aqi
        if was_alerted_recently and last_aqi and abs(curr_aqi - last_aqi) < 20:
            return False

        message = (
            "Air quality in {city} {zipcode} has changed to {curr_aqi_level} (AQI {curr_aqi}).\n"
            "\n"
            'Reply "M" for Menu or "E" to end alerts.'
        ).format(
            city=self.zipcode.city.name,
            zipcode=self.zipcode.zipcode,
            curr_aqi_level=curr_aqi_level.display,
            curr_aqi=curr_aqi,
        )
        if not self.send_message(message):
            return False

        self.last_alert_sent_at = timestamp()
        self.last_pm25 = curr_pm25
        self.num_alerts_sent += 1
        db.session.commit()

        self.log_event(EventType.ALERT, zipcode=self.zipcode.zipcode, pm25=curr_pm25)

        return True

    def request_share(self) -> bool:
        if not self.is_in_send_window:
            return False

        if self.created_at >= now() - datetime.timedelta(days=7):
            return False

        # Double check that we're all good to go
        share_window_start, share_window_end = self.get_share_window()
        if (
            not self.last_alert_sent_at
            or self.last_alert_sent_at <= share_window_start
            or self.last_alert_sent_at >= share_window_end
        ):
            return False

        # Check the last share request we sent was a long time ago
        share_request = self.get_last_share_request()
        if share_request and share_request.timestamp >= self.get_share_request_cutoff():
            return False

        message = (
            "Has Hazebot been helpful? "
            "We’re looking for ways to grow and improve, and we’d love your help. "
            "Save our contact and share Hazebot with a friend, or text “feedback” to send feedback."
        )
        if not self.send_message(message):
            return False

        Event.query.create(self.id, EventType.SHARE_REQUEST)
        return True

    #
    # Events
    #

    def log_event(self, event_type: EventType, **event_data: typing.Any) -> Event:
        return Event.query.create(self.id, event_type, **event_data)

    def _get_last_event_by_type(self, event_type: EventType) -> typing.Optional[Event]:
        return (
            Event.query.filter(Event.client_id == self.id)
            .filter(Event.type_code == event_type)
            .order_by(Event.timestamp.desc())
            .first()
        )

    def get_last_alert(self) -> typing.Optional[Event]:
        return self._get_last_event_by_type(EventType.ALERT)

    def get_last_share_request(self) -> typing.Optional[Event]:
        return self._get_last_event_by_type(EventType.SHARE_REQUEST)

    def get_last_client_event(self) -> typing.Optional[Event]:
        return (
            Event.query.filter(Event.client_id == self.id)
            .filter(
                ~Event.type_code.in_([EventType.ALERT, EventType.SHARE_REQUEST])
            )  # filter for only inbound events
            .order_by(Event.timestamp.desc())
            .first()
        )

    def get_last_client_event_type(self) -> typing.Optional[EventType]:
        last_event = self.get_last_client_event()
        if last_event:
            return EventType(last_event.type_code)
        return None

    def should_accept_feedback(self) -> bool:
        last_event = self.get_last_client_event()
        return bool(
            last_event
            and last_event.type_code
            in (EventType.FEEDBACK_BEGIN, EventType.UNSUBSCRIBE)
            and now() - last_event.timestamp < Client.FEEDBACK_RESPONSE_TIME
        )
