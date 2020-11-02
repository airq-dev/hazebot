from flask_sqlalchemy import BaseQuery

from airq.config import db


class SensorQuery(BaseQuery):
    def get_last_updated_at(self) -> int:
        result = (
            self.order_by(Sensor.updated_at.desc())
            .with_entities(Sensor.updated_at)
            .first()
        )
        if result:
            return result[0]
        return 0


class Sensor(db.Model):  # type: ignore
    __tablename__ = "sensors"

    query_class = SensorQuery

    id = db.Column(db.Integer(), nullable=False, primary_key=True)
    # The pm25 at the instant this reading was reported
    latest_reading = db.Column(db.Float(), nullable=False)
    # The pm25 over the past 10 minutes
    pm25_10 = db.Column(db.Float(), nullable=True)
    humidity = db.Column(db.Float(), nullable=True)
    updated_at = db.Column(db.Integer(), nullable=False)
    latitude = db.Column(db.Float(), nullable=False)
    longitude = db.Column(db.Float(), nullable=False)
    geohash_bit_1 = db.Column(db.String(), nullable=False)
    geohash_bit_2 = db.Column(db.String(), nullable=False)
    geohash_bit_3 = db.Column(db.String(), nullable=False)
    geohash_bit_4 = db.Column(db.String(), nullable=False)
    geohash_bit_5 = db.Column(db.String(), nullable=False)
    geohash_bit_6 = db.Column(db.String(), nullable=False)
    geohash_bit_7 = db.Column(db.String(), nullable=False)
    geohash_bit_8 = db.Column(db.String(), nullable=False)
    geohash_bit_9 = db.Column(db.String(), nullable=False)
    geohash_bit_10 = db.Column(db.String(), nullable=False)
    geohash_bit_11 = db.Column(db.String(), nullable=False)
    geohash_bit_12 = db.Column(db.String(), nullable=False)

    def __repr__(self) -> str:
        return f"<Sensor {self.id}: {self.latest_reading}>"

    @property
    def geohash(self) -> str:
        return "".join([getattr(self, f"geohash_bit_{i}") for i in range(1, 13)])
