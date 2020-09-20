import dataclasses
import enum
import typing

from flask_sqlalchemy import BaseQuery

from airq.config import db
from airq.lib import clock


class MessageType(enum.IntEnum):
    QUALITY = 1
    DETAILS = 2
    LAST = 3
    MENU = 4
    ABOUT = 5
    UNSUBSCRIBE = 6
    ALERT = 7


class MessageQuery(BaseQuery):
    def create(
        self, client_id: int, type_code: MessageType, **data: typing.Any
    ) -> "Message":
        message = Message(
            client_id=client_id, type_code=type_code, json_data=data or {}
        )
        message.validate()
        db.session.add(message)
        db.session.commit()


class MessageData:
    pass


@dataclasses.dataclass
class QualityMessageData(MessageData):
    zipcode: str
    pm25: float


@dataclasses.dataclass
class DetailsMessageData(MessageData):
    zipcode: str
    recommendations: typing.List[str]
    pm25: float
    num_sensors: int


@dataclasses.dataclass
class MenuMessageData(MessageData):
    pass


@dataclasses.dataclass
class AboutMessageData(MessageData):
    pass


@dataclasses.dataclass
class UnsubscribeMessageData(MessageData):
    zipcode: str


@dataclasses.dataclass
class AlertMessageData(MessageData):
    zipcode: str
    pm25: float


class Message(db.Model):
    __tablename__ = "messages"

    query_class = MessageQuery

    client_id = db.Column(
        db.Integer(),
        db.ForeignKey("clients.id", name="messages_client_id_fkey"),
        nullable=False,
    )
    type_code = db.Column(db.Integer(), nullable=False, index=True)
    timestamp = db.Column(db.Integer(), nullable=False, default=clock.timestamp)
    json_data = db.Column(db.JSON(), nullable=False)

    __table_args__ = (db.PrimaryKeyConstraint("client_id", "type_code", "timestamp"),)

    def __repr__(self) -> str:
        return f"<Message {self.message_type}>"

    @property
    def data(self) -> MessageData:
        if not hasattr(self, "_data"):
            self._data = self.validate()
        return self._data

    def validate(self) -> MessageData:
        if self.type_code == MessageType.QUALITY:
            spec = QualityMessageData
        elif self.type_code == MessageType.DETAILS:
            spec = DetailsMessageData
        elif self.type_code == MessageType.LAST:
            spec = QualityMessageData
        elif self.type_code == MessageType.MENU:
            spec = MenuMessageData
        elif self.type_code == MessageType.ABOUT:
            spec = AboutMessageData
        elif self.type_code == MessageType.UNSUBSCRIBE:
            spec = UnsubscribeMessageData
        elif self.type_code == MessageType.ALERT:
            spec = AlertMessageData
        else:
            raise Exception(f"Unknown message type {self.message_type}")

        return spec(**self.json_data)
