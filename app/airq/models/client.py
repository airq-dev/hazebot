import enum

from airq.config import db


class ClientIdentifierType(enum.Enum):
    PHONE_NUMBER = 1
    IP = 2


class Client(db.Model):  # type: ignore
    __tablename__ = "clients"

    id = db.Column(db.Integer(), primary_key=True)
    identifier = db.Column(db.String(), nullable=False)
    type_code = db.Column(db.Enum(ClientIdentifierType), nullable=False)

    __table_args__ = (
        db.Index(
            "_client_identifier_type_code", "identifier", "type_code", unique=True,
        ),
    )
