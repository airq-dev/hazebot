import datetime
import typing

from airq.settings import db


class Sensor(db.Model):  # type: ignore
    __tablename__ = "sensors"

    id = db.Column(db.Integer(), nullable=False, primary_key=True)
    reading = db.Column(db.Float(), nullable=False)
    updated_at = db.Column(db.Integer(), nullable=False)

    def __repr__(self) -> str:
        return f"<Sensor {self.id}: {self.reading}>"


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
    pm25 = sensor_data.get("PM2_5Value")
    if not pm25:
        return False
    try:
        pm25 = float(pm25)
    except (TypeError, ValueError):
        return False
    if pm25 <= 0 or pm25 > 1000:
        # Something is very wrong
        return False

    return True


def upsert_sensor_readings(mappings: typing.List[typing.Dict[str, typing.Any]]):
    sensor_ids = [m["id"] for m in mappings]
    existing_ids = {
        r[0]
        for r in Sensor.query.with_entities(Sensor.id)
        .filter(Sensor.id.in_(sensor_ids))
        .all()
    }
    sensors_to_insert = []
    sensors_to_update = []
    for m in mappings:
        if m["id"] in existing_ids:
            sensors_to_update.append(m)
        else:
            sensors_to_insert.append(m)
    db.session.bulk_insert_mappings(Sensor, sensors_to_insert)
    db.session.bulk_update_mappings(Sensor, sensors_to_update)
    db.session.commit()


def get_sensors(sensor_ids: typing.Iterable[int]) -> typing.List[Sensor]:
    return Sensor.query.filter(Sensor.id.in_(sensor_ids)).filter(
        Sensor.updated_at >= datetime.datetime.now().timestamp() - (60 * 20)
    )
