import datetime

from airq import geodb
from airq.settings import db


class User(db.Model):  # type: ignore
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    phone_number = db.Column(db.String(20), unique=True, index=True, nullable=False)

    def __repr__(self) -> str:
        return f"<User {self.phone_number}>"


class Request(db.Model):  # type: ignore
    __tablename__ = "requests"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    zipcode = db.Column(db.String(5), index=True, nullable=False)
    count = db.Column(db.Integer, nullable=False)
    first_ts = db.Column(db.Integer, nullable=False)
    last_ts = db.Column(db.Integer, nullable=False)

    def __repr__(self) -> str:
        return f"<Request {self.zipcode}>"


def insert_request(phone_number: str, zipcode: str):
    if not geodb.get_zipcode_raw(zipcode):
        return

    user = User.query.filter_by(phone_number=phone_number).first()
    if user is None:
        user = User(phone_number=phone_number)
        db.session.add(user)
        db.session.commit()

    request = Request.query.filter_by(zipcode=zipcode, user_id=user.id).first()
    now = datetime.datetime.now().timestamp()
    if request is None:
        request = Request(
            user_id=user.id, zipcode=zipcode, count=1, first_ts=now, last_ts=now
        )
        db.session.add(request)
    else:
        request.count += 1
        request.last_ts = now
    db.session.commit()
