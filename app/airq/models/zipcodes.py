import datetime
import typing

from airq.lib.geo import haversine_distance
from airq.lib.readings import Pm25
from airq.lib.readings import pm25_to_aqi
from airq.models.cities import City
from airq.config import db


class Zipcode(db.Model):  # type: ignore
    __tablename__ = "zipcodes"

    id = db.Column(db.Integer(), nullable=False, primary_key=True)
    zipcode = db.Column(db.String(), nullable=False, unique=True, index=True)
    city_id = db.Column(db.Integer(), db.ForeignKey("cities.id"), nullable=False)
    latitude = db.Column(db.Float(asdecimal=True), nullable=False)
    longitude = db.Column(db.Float(asdecimal=True), nullable=False)
    timezone = db.Column(db.String(), nullable=True)

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

    pm25 = db.Column(db.Float(), nullable=False, index=True, server_default="0")
    pm25_updated_at = db.Column(
        db.Integer(), nullable=False, index=True, server_default="0"
    )
    num_sensors = db.Column(db.Integer(), nullable=False, server_default="0")
    min_sensor_distance = db.Column(db.Float(), nullable=False, server_default="0")
    max_sensor_distance = db.Column(db.Float(), nullable=False, server_default="0")

    city = db.relationship("City")
    requests = db.relationship("Request")

    def __repr__(self) -> str:
        return f"<Zipcode {self.zipcode}>"

    def __new__(cls, *args, **kwargs):
        obj = super().__new__(cls)
        obj._distance_cache = {}
        return obj

    @classmethod
    def get_by_zipcode(cls, zipcode: str) -> typing.Optional["Zipcode"]:
        return cls.query.filter_by(zipcode=zipcode).first()

    @property
    def geohash(self) -> str:
        return "".join([getattr(self, f"geohash_bit_{i}") for i in range(1, 13)])

    @property
    def pm25_level(self) -> Pm25:
        return Pm25.from_measurement(self.pm25)

    @classmethod
    def cutoff(cls) -> float:
        return datetime.datetime.now().timestamp() - (60 * 30)

    @property
    def is_pm25_stale(self) -> bool:
        return self.pm25_updated_at < self.cutoff()

    @property
    def aqi(self) -> typing.Optional[int]:
        return pm25_to_aqi(self.pm25)

    def distance(self, other: "Zipcode") -> float:
        if other.id not in self._distance_cache:
            self._distance_cache[other.id] = haversine_distance(
                other.longitude, other.latitude, self.longitude, self.latitude,
            )
        return self._distance_cache[other.id]

    def get_recommendations(self, num_desired: int) -> typing.List["Zipcode"]:
        if not self.pm25_level or self.is_pm25_stale:
            return []

        cutoff = self.cutoff()
        zipcodes = (
            Zipcode.query.filter(Zipcode.pm25_updated_at > cutoff)
            .filter(Zipcode.pm25 < self.pm25_level)
            .all()
        )
        # Sorting 40000 zipcodes in memory is surprisingly fast.
        #
        # I wouldn't be surprised if doing this huge fetch every time actually leads to better
        # performance since Postgres can easily cache the whole query.
        #
        return sorted(zipcodes, key=lambda z: self.distance(z))[:num_desired]
