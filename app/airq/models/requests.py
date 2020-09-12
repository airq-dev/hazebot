import datetime
import enum
import typing

from airq.config import db
from airq.models.zipcodes import Zipcode


class ClientIdentifierType(enum.Enum):
    PHONE_NUMBER = 1
    IP = 2


class Request(db.Model):  # type: ignore
    __tablename__ = "requests"

    id = db.Column(db.Integer, primary_key=True)
    zipcode = db.Column(db.String(5), index=True, nullable=False)
    client_identifier = db.Column(db.String(100), nullable=False)
    client_identifier_type = db.Column(db.Enum(ClientIdentifierType), nullable=False)
    count = db.Column(db.Integer, nullable=False)
    first_ts = db.Column(db.Integer, nullable=False)
    last_ts = db.Column(db.Integer, nullable=False)

    __table_args__ = (
        db.Index(
            "_zipcode_client_identifier_client_identifier_type_index",
            "zipcode",
            "client_identifier",
            "client_identifier_type",
            unique=True,
        ),
    )

    def __repr__(self) -> str:
        return f"<Request {self.zipcode}>"

    @classmethod
    def increment(
        cls, zipcode: str, identifier: str, identifier_type: ClientIdentifierType
    ):
        if not Zipcode.get_by_zipcode(zipcode):
            return

        request = cls.query.filter_by(
            client_identifier=identifier,
            client_identifier_type=identifier_type,
            zipcode=zipcode,
        ).first()
        now = datetime.datetime.now().timestamp()
        if request is None:
            request = cls(
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

    @classmethod
    def get_last_zipcode(
        cls, identifier: str, identifier_type: ClientIdentifierType
    ) -> typing.Optional[str]:
        row = (
            cls.query.with_entities(cls.zipcode)
            .filter_by(
                client_identifier=identifier, client_identifier_type=identifier_type
            )
            .order_by(cls.last_ts.desc())
            .first()
        )
        if row:
            return row[0]
        return None
