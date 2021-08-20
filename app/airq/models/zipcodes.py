import dataclasses
import typing

from flask_sqlalchemy import BaseQuery

from airq.lib.clock import timestamp
from airq.lib.geo import haversine_distance
from airq.lib.readings import ConversionFactor
from airq.lib.readings import Pm25
from airq.lib.readings import Readings
from airq.config import db
from airq.models.metrics import Metric


@dataclasses.dataclass
class ZipcodeMetrics:
    num_sensors: int
    min_sensor_distance: int
    max_sensor_distance: int
    sensor_ids: typing.List[int]


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
    humidity = db.Column(db.Float(), nullable=False, server_default="0")
    pm_cf_1 = db.Column(db.Float(), nullable=False, server_default="0")
    pm25_updated_at = db.Column(
        db.Integer(), nullable=False, index=True, server_default="0"
    )

    metrics_data = db.Column(db.JSON(), nullable=True)

    city = db.relationship("City")

    def __repr__(self) -> str:
        return f"<Zipcode {self.zipcode}>"

    def __new__(cls, *args, **kwargs):
        obj = super().__new__(cls)
        obj._distance_cache = {}
        return obj

    def get_latest_metric(self) -> Metric:
        if not hasattr(self, "_latest_metric"):
            self._latest_metric = (
                Metric.query.filter_by(zipcode_id=self.id)
                .order_by(Metric.created_at.desc())
                .first()
            )
        return self._latest_metric

    def get_readings(self) -> Readings:
        return self.get_latest_metric().get_readings()

    @property
    def has_readings(self) -> bool:
        return self.get_latest_metric() is not None

    @property
    def num_sensors(self) -> int:
        return self.get_latest_metric().num_sensors

    @property
    def max_sensor_distance(self) -> int:
        return self.get_latest_metric().max_sensor_distance

    @property
    def min_sensor_distance(self) -> int:
        return self.get_latest_metric().min_sensor_distance

    @property
    def geohash(self) -> str:
        """This zipcode's geohash."""
        return "".join([getattr(self, f"geohash_bit_{i}") for i in range(1, 13)])

    @classmethod
    def pm25_stale_cutoff(cls) -> float:
        """Timestamp before which pm25 measurements are considered stale."""
        return timestamp() - (60 * 60)

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

    def get_aqi(self, conversion_factor: ConversionFactor) -> int:
        """The AQI for this zipcode (e.g., 35) as determined by the provided strategy."""
        return self.get_readings().get_aqi(conversion_factor)

    def get_pm25(self, conversion_factor: ConversionFactor) -> float:
        """Current pm25 for this client, as determined by the provided strategy."""
        return self.get_readings().get_pm25(conversion_factor)

    def get_pm25_level(self, conversion_factor: ConversionFactor) -> Pm25:
        """The pm25 category for this zipcode (e.g., Moderate)."""
        return self.get_readings().get_pm25_level(conversion_factor)

    def get_recommendations(
        self, num_desired: int, conversion_factor: ConversionFactor
    ) -> typing.List["Zipcode"]:
        """Get n recommended zipcodes near this zipcode, sorted by distance."""
        if self.is_pm25_stale:
            return []

        cutoff = self.pm25_stale_cutoff()

        # TODO: Make this faster somehow?
        curr_pm25_level = self.get_pm25_level(conversion_factor)
        zipcodes = [
            z
            for z in Zipcode.query.filter(Zipcode.pm25_updated_at > cutoff).all()
            if z.get_pm25_level(conversion_factor) < curr_pm25_level
        ]

        return sorted(zipcodes, key=lambda z: self.distance(z))[:num_desired]
