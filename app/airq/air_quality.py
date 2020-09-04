import dataclasses
import logging
import typing

from airq import cache
from airq import geodb
from airq import purpleair
from airq import util


logger = logging.getLogger(__name__)


DESIRED_NUM_SENSORS = 10


MAX_SENSOR_RADIUS = 25


@dataclasses.dataclass(frozen=True)
class Sensor:
    sensor_id: int
    distance: float
    pm25: float


@dataclasses.dataclass(frozen=True)
class Metrics:
    pm25: float
    num_sensors: int
    max_sensor_distance: float
    readings: typing.List[float]

    @property
    def pm25_display(self) -> str:
        return util.get_pm25_display(self.pm25)


def _get_sensor_distances(zipcode: str,) -> typing.Dict[int, float]:

    #
    # This is a map from sensor ids to their distance from this zip.
    # We exclude them if they're "dead"; that is, not returning a valid reading.
    # If we do have dead sensors, we query the DB for other nearby sensors
    # so that we can (hopefully) find 10 active nearby sensors to read from.
    #

    sensor_to_distance: typing.Dict[int, float] = cache.SENSOR_DISTANCE.get(zipcode, {})
    already_seen_sensor_ids = list(sensor_to_distance)
    for sensor_id in cache.DEAD_SENSORS.get_many(sensor_to_distance):
        del sensor_to_distance[sensor_id]

    num_missing = DESIRED_NUM_SENSORS - len(sensor_to_distance)
    if num_missing:
        sensor_to_distance.update(
            geodb.get_sensor_distances(
                zipcode,
                exclude_ids=already_seen_sensor_ids,
                num_desired=num_missing,
                max_radius=MAX_SENSOR_RADIUS,
            )
        )
        cache.SENSOR_DISTANCE.set(zipcode, sensor_to_distance)

    return sensor_to_distance


def _get_sensors(zipcode: str) -> typing.List[Sensor]:
    sensor_to_distance = _get_sensor_distances(zipcode)
    pm25_readings = cache.PM25.get_many(sensor_to_distance)
    missing_sensor_ids = set(sensor_to_distance) - set(pm25_readings)
    if missing_sensor_ids:
        pm25_readings.update(purpleair.get_readings(missing_sensor_ids))
    return sorted(
        [
            Sensor(sensor_id, sensor_to_distance[sensor_id], pm25)
            for sensor_id, pm25 in pm25_readings.items()
        ],
        key=lambda sensor: sensor.distance,
    )


def get_metrics(zipcode: str) -> typing.Optional[Metrics]:
    sensors = _get_sensors(zipcode)
    if not sensors:
        return None
    return Metrics(
        pm25=round(sum(s.pm25 for s in sensors) / len(sensors), ndigits=3),
        num_sensors=len(sensors),
        max_sensor_distance=round(sensors[-1].distance, ndigits=3),
        readings=[round(s.pm25, ndigits=3) for s in sensors],
    )
