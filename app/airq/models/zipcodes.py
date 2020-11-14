import typing

from flask_sqlalchemy import BaseQuery

from airq.lib.clock import timestamp
from airq.lib.geo import haversine_distance
from airq.lib.readings import Pm25
from airq.lib.readings import pm25_to_aqi
from airq.models.cities import City
from airq.config import db


class ZipcodeQuery(BaseQuery):
    def get_by_zipcode(self, zipcode: str) -> typing.Optional["Zipcode"]:
        return self.filter_by(zipcode=zipcode).first()


class Zipcode(db.Model):  # type: ignore
    __tablename__ = "zipcodes"

    query_class = ZipcodeQuery

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

    metrics_data = db.Column(db.JSON(), nullable=True)
    num_sensors = db.Column(db.Integer(), nullable=False, server_default="0")
    min_sensor_distance = db.Column(db.Float(), nullable=False, server_default="0")
    max_sensor_distance = db.Column(db.Float(), nullable=False, server_default="0")

    city = db.relationship("City")

    def __repr__(self) -> str:
        return f"<Zipcode {self.zipcode}>"

    def __new__(cls, *args, **kwargs):
        obj = super().__new__(cls)
        obj._distance_cache = {}
        return obj

    @property
    def geohash(self) -> str:
        """This zipcode's geohash."""
        return "".join([getattr(self, f"geohash_bit_{i}") for i in range(1, 13)])

    @property
    def aqi(self) -> typing.Optional[int]:
        """The AQI for this zipcode (e.g., 35)."""
        return pm25_to_aqi(self.pm25)

    @property
    def pm25_level(self) -> Pm25:
        """The pm25 category for this zipcode (e.g., Moderate)."""
        return Pm25.from_measurement(self.pm25)

    @classmethod
    def pm25_stale_cutoff(cls) -> float:
        """Timestamp before which pm25 measurements are considered stale."""
        return timestamp() - (60 * 30)

    @property
    def is_pm25_stale(self) -> bool:
        """Whether this zipcode's pm25 measurements are considered stale."""
        return self.pm25_updated_at < self.pm25_stale_cutoff()

    def distance(self, other: "Zipcode") -> float:
        """Distance between this zip and the given zip."""
        if other.id in self._distance_cache:
            return self._distance_cache[other.id]
        if self.id in other._distance_cache:
            return other._distance_cache[self.id]
        self._distance_cache[other.id] = haversine_distance(
            other.longitude,
            other.latitude,
            self.longitude,
            self.latitude,
        )
        return self._distance_cache[other.id]

    def get_recommendations(self, num_desired: int) -> typing.List["Zipcode"]:
        """Get n recommended zipcodes near this zipcode, sorted by distance."""
        if not self.pm25_level or self.is_pm25_stale:
            return []

        cutoff = self.pm25_stale_cutoff()
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
