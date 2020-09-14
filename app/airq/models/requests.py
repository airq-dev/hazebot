from airq.config import db


class Request(db.Model):  # type: ignore
    __tablename__ = "requests"

    id = db.Column(db.Integer, primary_key=True)
    zipcode = db.Column(db.String(5), index=True, nullable=False)
    zipcode_id = db.Column(
        db.Integer(),
        db.ForeignKey("zipcodes.id", name="requests_zipcode_id_fkey"),
        nullable=True,
    )
    client_id = db.Column(
        db.Integer(),
        db.ForeignKey("clients.id", name="requests_client_id_fkey"),
        nullable=False,
    )
    count = db.Column(db.Integer, nullable=False)
    first_ts = db.Column(db.Integer, nullable=False)
    last_ts = db.Column(db.Integer, nullable=False)

    client = db.relationship("Client")
    # zipcode = db.relationship('Zipcode', back_populates='requests')

    def __repr__(self) -> str:
        return f"<Request {self.zipcode}>"
