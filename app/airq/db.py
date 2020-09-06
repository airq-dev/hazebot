import datetime
import enum

from airq import geodb
from airq.settings import db


class ClientIdentifierType(enum.Enum):
    PHONE_NUMBER = 1
    IP = 2


class Request(db.Model):  # type: ignore
    __tablename__ = "requests"

    id = db.Column(db.Integer, primary_key=True)
    client_identifier = db.Column(db.String(100), nullable=False)
    client_identifier_type = db.Column(db.Enum(ClientIdentifierType), nullable=False)
    zipcode = db.Column(db.String(5), index=True, nullable=False)
    count = db.Column(db.Integer, nullable=False)
    first_ts = db.Column(db.Integer, nullable=False)
    last_ts = db.Column(db.Integer, nullable=False)

    __table_args__ = (
        db.Index(
            "_client_identifier_client_identifier_type_index",
            "client_identifier",
            "client_identifier_type",
            unique=True,
        ),
    )

    def __repr__(self) -> str:
        return f"<Request {self.zipcode}>"


def insert_request(
    zipcode: str, identifier: str, identifier_type: ClientIdentifierType
):
    if not geodb.get_zipcode_raw(zipcode):
        return

    request = Request.query.filter_by(
        client_identifier=identifier,
        client_identifier_type=identifier_type,
        zipcode=zipcode,
    ).first()
    now = datetime.datetime.now().timestamp()
    if request is None:
        request = Request(
            client_identifier=identifier,
            client_identifier_type=identifier_type,
            zipcode=zipcode,
            count=1,
            first_ts=now,
            last_ts=now,
        )
        db.session.add(request)
    else:
        request.count += 1
        request.last_ts = now
    db.session.commit()
