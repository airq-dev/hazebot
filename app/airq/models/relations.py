from airq.config import db


class SensorZipcodeRelation(db.Model):  # type: ignore
    __tablename__ = "sensors_zipcodes"

    sensor_id = db.Column(
        db.Integer(), db.ForeignKey("sensors.id"), nullable=False, primary_key=True
    )
    zipcode_id = db.Column(
        db.Integer(), db.ForeignKey("zipcodes.id"), nullable=False, primary_key=True
    )
    # Unit: KM
    distance = db.Column(db.Float(), nullable=False)

    def __repr__(self) -> str:
        return f"<SensorZipcodeRelation {self.sensor_id} - {self.zipcode_id} - {self.distance}>"
