import dataclasses
import typing

from flask_sqlalchemy import BaseQuery

from airq.lib.clock import timestamp
from airq.lib.geo import haversine_distance
from airq.lib.readings import ConversionStrategy
from airq.lib.readings import Pm25
from airq.lib.readings import Readings
from airq.config import db


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

    def get_metrics(self) -> ZipcodeMetrics:
        if not hasattr(self, "_metrics"):
            self._metrics = ZipcodeMetrics(
                num_sensors=self.metrics_data["num_sensors"],
                max_sensor_distance=self.metrics_data["max_sensor_distance"],
                min_sensor_distance=self.metrics_data["min_sensor_distance"],
                sensor_ids=self.metrics_data["sensor_ids"],
            )
        return self._metrics

    def get_readings(self) -> Readings:
        return Readings(pm25=self.pm25, pm_cf_1=self.pm_cf_1, humidity=self.humidity)

    @property
    def num_sensors(self) -> int:
        return self.get_metrics().num_sensors

    @property
    def max_sensor_distance(self) -> int:
        return self.get_metrics().max_sensor_distance

    @property
    def min_sensor_distance(self) -> int:
        return self.get_metrics().min_sensor_distance

    @property
    def geohash(self) -> str:
        """This zipcode's geohash."""
        return "".join([getattr(self, f"geohash_bit_{i}") for i in range(1, 13)])

    @classmethod
    def pm25_stale_cutoff(cls) -> float:
        """Timestamp before which pm25 measurements are considered stale."""
        return timestamp() - (60 * 120)

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

    def get_current_aqi(self, conversion_strategy: ConversionStrategy) -> int:
        """The AQI for this zipcode (e.g., 35) as determined by the provided strategy."""
        return self.get_readings().get_aqi(conversion_strategy)

    def get_current_pm25(self, conversion_strategy: ConversionStrategy) -> float:
        """Current pm25 for this client, as determined by the provided strategy."""
        return self.get_readings().get_pm25(conversion_strategy)

    def get_pm25_level(self, conversion_strategy: ConversionStrategy) -> Pm25:
        """The pm25 category for this zipcode (e.g., Moderate)."""
        return self.get_readings().get_pm25_level(conversion_strategy)

    def get_recommendations(
        self, num_desired: int, conversion_strategy: ConversionStrategy
    ) -> typing.List["Zipcode"]:
        """Get n recommended zipcodes near this zipcode, sorted by distance."""
        if self.is_pm25_stale:
            return []

        cutoff = self.pm25_stale_cutoff()

        # TODO: Make this faster somehow?
        curr_pm25_level = self.get_pm25_level(conversion_strategy)
        zipcodes = [
            z
            for z in Zipcode.query.filter(Zipcode.pm25_updated_at > cutoff).all()
            if z.get_pm25_level(conversion_strategy) < curr_pm25_level
        ]

        return sorted(zipcodes, key=lambda z: self.distance(z))[:num_desired]
