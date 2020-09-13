import datetime
import enum

from airq.config import db
from airq.models.client import Client
from airq.models.client import ClientIdentifierType
from airq.models.zipcodes import Zipcode


class Request(db.Model):  # type: ignore
    __tablename__ = "requests"

    id = db.Column(db.Integer, primary_key=True)
    zipcode = db.Column(db.String(5), index=True, nullable=False)
    client_id = db.Column(
        db.Integer(),
        db.ForeignKey("clients.id", name="requests_client_id_fkey"),
        nullable=False,
    )
    count = db.Column(db.Integer, nullable=False)
    first_ts = db.Column(db.Integer, nullable=False)
    last_ts = db.Column(db.Integer, nullable=False)

    def __repr__(self) -> str:
        return f"<Request {self.zipcode}>"


def insert_request(
    zipcode: str, identifier: str, identifier_type: ClientIdentifierType
):
    if not Zipcode.query.filter_by(zipcode=zipcode).first():
        return

    client = Client.query.filter_by(
        identifier=identifier, type_code=identifier_type
    ).first()

    if client is None:
        client = Client(identifier=identifier, type_code=identifier_type)
        db.session.add(client)
        db.session.commit()
        request = None
    else:
        request = Request.query.filter_by(client_id=client.id, zipcode=zipcode,).first()

    now = datetime.datetime.now().timestamp()
    if request is None:
        request = Request(
            client_id=client.id, zipcode=zipcode, count=1, first_ts=now, last_ts=now,
        )
        db.session.add(request)
    else:
        request.count += 1
        request.last_ts = now
    db.session.commit()
