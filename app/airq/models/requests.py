from airq.config import db


class Request(db.Model):  # type: ignore
    __tablename__ = "requests"

    zipcode_id = db.Column(
        db.Integer(),
        db.ForeignKey("zipcodes.id", name="requests_zipcode_id_fkey"),
        nullable=False,
        primary_key=True,
    )
    client_id = db.Column(
        db.Integer(),
        db.ForeignKey("clients.id", name="requests_client_id_fkey"),
        nullable=False,
        primary_key=True,
    )
    count = db.Column(db.Integer, nullable=False)
    first_ts = db.Column(db.Integer, nullable=False)
    last_ts = db.Column(db.Integer, nullable=False)

    client = db.relationship("Client")
    zipcode = db.relationship("Zipcode")

    def __repr__(self) -> str:
        return f"<Request {self.client_id} - {self.zipcode_id}>"
