import collections
import datetime
import dataclasses
import enum
import pytz
import typing

from flask_sqlalchemy import BaseQuery
from sqlalchemy import desc
from sqlalchemy import func

from airq.config import db
from airq.lib import clock


class EventSchema(typing.Protocol):
    def __call__(self, **kwargs: typing.Any) -> object:
        ...


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
        keys = sorted(m.name for m in EventType)
        stats: typing.Dict[str, typing.Dict[str, int]] = collections.defaultdict(
            lambda: {name: 0 for name in keys}
        )
        totals = {name: 0 for name in keys}
        for date, type_code, count in (
            self.filter(Event.timestamp > clock.now() - datetime.timedelta(days=30))
            .with_entities(
                func.DATE(func.timezone("PST", Event.timestamp)).label("date"),
                Event.type_code,
                func.count(Event.id),
            )
            .group_by("date", Event.type_code)
            .order_by(desc("date"))
            .all()
        ):
            send_date = date.strftime("%Y-%m-%d")
            event_type = EventType(type_code)
            stats[send_date][event_type.name] = count
            totals[event_type.name] += count
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
            return MenuEventSchema
        elif self.type_code == EventType.ABOUT:
            return AboutEventSchema
        elif self.type_code == EventType.UNSUBSCRIBE:
            return SubscribeEventSchema
        elif self.type_code == EventType.ALERT:
            return AlertEventSchema
        elif self.type_code == EventType.FEEDBACK_BEGIN:
            return FeedbackBeginEventSchema
        elif self.type_code == EventType.FEEDBACK_RECEIVED:
            return FeedbackReceivedEventSchema
        elif self.type_code == EventType.RESUBSCRIBE:
            return SubscribeEventSchema
        else:
            raise Exception(f"Unknown event type {self.type_code}")

    def validate(self) -> typing.Dict[str, typing.Any]:
        schema = self._get_schema()
        return dataclasses.asdict(schema(**self.json_data))


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
class MenuEventSchema:
    pass


@dataclasses.dataclass
class AboutEventSchema:
    pass


@dataclasses.dataclass
class SubscribeEventSchema:
    zipcode: str


@dataclasses.dataclass
class AlertEventSchema:
    zipcode: str
    pm25: float


@dataclasses.dataclass
class FeedbackBeginEventSchema:
    pass


@dataclasses.dataclass
class FeedbackReceivedEventSchema:
    feedback: str
