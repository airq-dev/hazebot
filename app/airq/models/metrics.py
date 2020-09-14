from airq.config import db

from airq.lib.readings import Pm25


class Metric(db.Model):  # type: ignore
    __tablename__ = "metrics"

    zipcode_id = db.Column(
        db.Integer(),
        db.ForeignKey("zipcodes.id", name="metrics_zipcodes_fkey"),
        primary_key=True,
        nullable=False,
    )
    timestamp = db.Column(db.Integer(), primary_key=True, nullable=False)
    value = db.Column(db.Float(), nullable=False)
    num_sensors = db.Column(db.Integer(), nullable=False)
    max_sensor_distance = db.Column(db.Float(), nullable=False)
    min_sensor_distance = db.Column(db.Float(), nullable=False)

    def __repr__(self) -> str:
        return f"<Metric {self.value} from {self.num_sensors}>"

    @property
    def pm25_level(self) -> Pm25:
        return Pm25.from_measurement(self.value)
