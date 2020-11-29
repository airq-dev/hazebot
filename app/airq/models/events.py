import collections
import datetime
import dataclasses
import enum
import typing

from flask_sqlalchemy import BaseQuery
from sqlalchemy import desc
from sqlalchemy import func

from airq.config import db
from airq.lib import clock


class EventSchema(typing.Protocol):
    def __call__(self, **kwargs: typing.Any) -> object:
        ...


@enum.unique
class EventType(enum.IntEnum):
    QUALITY = 1
    DETAILS = 2
    LAST = 3
    MENU = 4
    ABOUT = 5
    UNSUBSCRIBE = 6
    ALERT = 7
    RESUBSCRIBE = 8
    FEEDBACK_BEGIN = 9
    FEEDBACK_RECEIVED = 10
    UNSUBSCRIBE_AUTO = 11
    SHARE_REQUEST = 12
    LIST_PREFS = 13
    SET_PREF_REQUEST = 14
    SET_PREF = 15


class EventQuery(BaseQuery):
    def create(
        self, client_id: int, type_code: EventType, **data: typing.Any
    ) -> "Event":
        event = Event(client_id=client_id, type_code=type_code, json_data=data or {})
        event.validate()
        db.session.add(event)
        db.session.commit()
        return event

    def get_stats(self) -> typing.Dict[str, typing.Dict[str, int]]:
        cutoff = clock.now() - datetime.timedelta(days=30)
        metrics = [m.name for m in EventType]
        metrics.append("NEW_USERS")
        keys = sorted(metrics)
        stats: typing.Dict[str, typing.Dict[str, int]] = collections.defaultdict(
            lambda: {name: 0 for name in keys}
        )
        totals = {name: 0 for name in keys}
        for date, type_code, count in (
            self.filter(Event.timestamp > cutoff)
            .with_entities(
                func.DATE(func.timezone("PST", Event.timestamp)).label("date"),
                Event.type_code,
                func.count(Event.id),
            )
            .group_by("date", Event.type_code)
            .order_by(desc("date"))
            .all()
        ):
            event_date = date.strftime("%Y-%m-%d")
            event_type = EventType(type_code)
            stats[event_date][event_type.name] = count
            totals[event_type.name] += count

        # Ew.
        from airq.models.clients import Client

        for date, count in (
            Client.query.filter_phones()
            .filter(Client.created_at > cutoff)
            .with_entities(
                func.DATE(func.timezone("PST", Client.created_at)).label("date"),
                func.count(Client.id),
            )
            .group_by("date")
            .order_by(desc("date"))
            .all()
        ):
            join_date = date.strftime("%Y-%m-%d")
            stats[join_date]["NEW_USERS"] = count

        stats["TOTAL"] = totals
        return dict(stats)


class Event(db.Model):  # type: ignore
    __tablename__ = "events"

    query_class = EventQuery

    id = db.Column(db.Integer(), primary_key=True)
    client_id = db.Column(
        db.Integer(),
        db.ForeignKey("clients.id", name="events_client_id_fkey"),
        nullable=False,
        index=True,
    )
    type_code = db.Column(db.Integer(), nullable=False, index=True)
    timestamp = db.Column(
        db.TIMESTAMP(timezone=True), nullable=False, default=clock.now, index=True
    )
    json_data = db.Column(db.JSON(), nullable=False)

    def __repr__(self) -> str:
        return f"<Event {self.type_code}>"

    @property
    def data(self) -> typing.Dict[str, typing.Any]:
        if not hasattr(self, "_data"):
            self._data = self.validate()
        return self._data

    def _get_schema(self) -> EventSchema:
        if self.type_code == EventType.QUALITY:
            return QualityEventSchema
        elif self.type_code == EventType.DETAILS:
            return DetailsEventSchema
        elif self.type_code == EventType.LAST:
            return QualityEventSchema
        elif self.type_code == EventType.MENU:
            return EmptySchema
        elif self.type_code == EventType.ABOUT:
            return EmptySchema
        elif self.type_code == EventType.UNSUBSCRIBE:
            return SubscribeEventSchema
        elif self.type_code == EventType.ALERT:
            return AlertEventSchema
        elif self.type_code == EventType.FEEDBACK_BEGIN:
            return EmptySchema
        elif self.type_code == EventType.FEEDBACK_RECEIVED:
            return FeedbackReceivedEventSchema
        elif self.type_code == EventType.RESUBSCRIBE:
            return SubscribeEventSchema
        elif self.type_code == EventType.UNSUBSCRIBE_AUTO:
            return SubscribeEventSchema
        elif self.type_code == EventType.SHARE_REQUEST:
            return EmptySchema
        elif self.type_code == EventType.LIST_PREFS:
            return EmptySchema
        elif self.type_code == EventType.SET_PREF_REQUEST:
            return SetPrefRequestEventSchema
        elif self.type_code == EventType.SET_PREF:
            return SetPrefEventSchema
        else:
            raise Exception(f"Unknown event type {self.type_code}")

    def validate(self) -> typing.Dict[str, typing.Any]:
        schema = self._get_schema()
        json_data = typing.cast(typing.Dict[str, typing.Any], self.json_data)
        return dataclasses.asdict(schema(**json_data))


@dataclasses.dataclass
class QualityEventSchema:
    zipcode: str
    pm25: float


@dataclasses.dataclass
class DetailsEventSchema:
    zipcode: str
    recommendations: typing.List[str]
    pm25: float
    num_sensors: int


@dataclasses.dataclass
class EmptySchema:
    pass


@dataclasses.dataclass
class SubscribeEventSchema:
    zipcode: str


@dataclasses.dataclass
class AlertEventSchema:
    zipcode: str
    pm25: float


@dataclasses.dataclass
class FeedbackReceivedEventSchema:
    feedback: str


@dataclasses.dataclass
class SetPrefRequestEventSchema:
    pref_name: str


@dataclasses.dataclass
class SetPrefEventSchema:
    pref_name: str
    pref_value: typing.Any
