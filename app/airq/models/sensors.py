import datetime
import typing

from airq.config import db


class Sensor(db.Model):  # type: ignore
    __tablename__ = "sensors"

    id = db.Column(db.Integer(), nullable=False, primary_key=True)
    latest_reading = db.Column(db.Float(), nullable=False)
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


def is_valid_reading(sensor_data: typing.Dict[str, typing.Any]) -> bool:
    if sensor_data.get("DEVICE_LOCATIONTYPE") != "outside":
        return False
    if sensor_data.get("ParentID"):
        return False
    if sensor_data.get("LastSeen", 0) < datetime.datetime.now().timestamp() - (60 * 60):
        # Out of date / maybe dead
        return False
    if sensor_data.get("Flag"):
        # Flagged for an unusually high reading
        return False
    try:
        pm25 = float(sensor_data.get("PM2_5Value", 0))
    except (TypeError, ValueError):
        return False
    if pm25 <= 0 or pm25 > 1000:
        # Something is very wrong
        return False
    latitude = sensor_data.get("Lat")
    longitude = sensor_data.get("Lon")
    if latitude is None or longitude is None:
        return False

    return True
