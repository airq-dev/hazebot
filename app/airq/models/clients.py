import datetime
import enum
import typing

from airq.config import db
from airq.models.requests import Request
from airq.models.zipcodes import Zipcode


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

    @classmethod
    def get_or_create(
        cls, identifier: str, type_code: ClientIdentifierType
    ) -> "Client":
        client = cls.query.filter_by(identifier=identifier, type_code=type_code).first()
        if not client:
            client = cls(identifier=identifier, type_code=type_code)
            db.session.add(client)
            db.session.commit()
        return client

    def get_last_requested_zipcode(self) -> typing.Optional[Zipcode]:
        row = (
            Request.query.with_entities(Request.zipcode)
            .filter_by(client_id=self.id)
            .order_by(Request.last_ts.desc())
            .first()
        )
        if row:
            # TODO: FK between Request and Zipcode
            return Zipcode.get_by_zipcode(row[0])
        return None

    def log_request(self, zipcode: Zipcode):
        request = Request.query.filter_by(client_id=self.id, zipcode=zipcode.zipcode,).first()
        now = datetime.datetime.now().timestamp()
        if request is None:
            request = Request(
                client_id=self.id, zipcode=zipcode.zipcode, count=1, first_ts=now, last_ts=now,
            )
            db.session.add(request)
        else:
            request.count += 1
            request.last_ts = now
        db.session.commit()
