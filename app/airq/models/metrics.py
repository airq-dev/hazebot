import dataclasses
import typing

from datetime import timedelta
from flask_sqlalchemy import BaseQuery

from airq.config import db
from airq.lib.clock import now
from airq.lib.readings import Readings


@dataclasses.dataclass
class MetricDetails:
    num_sensors: int
    min_sensor_distance: int
    max_sensor_distance: int
    sensor_ids: typing.List[int]


class MetricQuery(BaseQuery):
    def filter_for_deletion(self) -> "MetricQuery":
        return self.filter(
            Metric.created_at < now() - timedelta(days=Metric.RETENTION_DAYS)
        )


class Metric(db.Model):  # type: ignore
    __tablename__ = "metrics"

    query_class = MetricQuery

    id = db.Column(db.Integer(), primary_key=True)
    zipcode_id = db.Column(
        db.Integer(),
        db.ForeignKey("zipcodes.id", name="metrics_zipcode_id_fkey"),
        nullable=False,
    )

    pm25 = db.Column(db.Float(), nullable=False)
    humidity = db.Column(db.Float(), nullable=False)
    pm_cf_1 = db.Column(db.Float(), nullable=False)
    details = db.Column(db.JSON(), nullable=False, default="{}")

    created_at = db.Column(
        db.TIMESTAMP(timezone=True), default=now, index=True, nullable=False
    )

    zipcode = db.relationship("Zipcode")

    RETENTION_DAYS = 3

    def get_readings(self) -> Readings:
        return Readings(pm25=self.pm25, pm_cf_1=self.pm_cf_1, humidity=self.humidity)

    def get_details(self) -> MetricDetails:
        if not hasattr(self, "_details"):
            self._details = MetricDetails(**self.details)
        return self._details

    @property
    def num_sensors(self) -> int:
        return self.get_details().num_sensors

    @property
    def max_sensor_distance(self) -> int:
        return self.get_details().max_sensor_distance

    @property
    def min_sensor_distance(self) -> int:
        return self.get_details().min_sensor_distance
