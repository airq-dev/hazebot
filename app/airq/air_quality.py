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


def _get_distances(zipcode: str) -> typing.Dict[int, float]:
    distances: typing.Dict[int, float] = cache.DISTANCE.get(zipcode, {})
    already_seen_sensor_ids = list(distances)
    for sensor_id in cache.DEAD.get_many(distances):
        del distances[sensor_id]

    num_missing = DESIRED_NUM_SENSORS - len(distances)
    if num_missing:
        distances.update(
            geodb.get_distances(
                zipcode,
                exclude_ids=already_seen_sensor_ids,
                num_desired=num_missing,
                max_radius=MAX_SENSOR_RADIUS,
            )
        )
        cache.DISTANCE.set(zipcode, distances)

    return distances


def _get_readings(sensor_ids: typing.Iterable[int]) -> typing.Dict[int, float]:
    readings = cache.PM25.get_many(sensor_ids)

    missing_sensor_ids = set(sensor_ids) - set(readings)
    if missing_sensor_ids:
        live_sensors = {}
        dead_sensors = {}
        for sensor_id, pm25 in purpleair.get_readings(missing_sensor_ids).items():
            if pm25 <= 0 or pm25 > 500:
                logger.warning(
                    "Marking sensor %s dead because its pm25 is %s", sensor_id, pm25,
                )
                dead_sensors[sensor_id] = True
            else:
                missing_sensor_ids.remove(sensor_id)
                live_sensors[sensor_id] = pm25

        if dead_sensors:
            cache.DEAD.set_many(dead_sensors)

        if live_sensors:
            cache.PM25.set_many(live_sensors)
            readings.update(live_sensors)

        if missing_sensor_ids:
            # This should be empty now if we've gotten pm25 info for every sensor.
            logger.warning("No results for ids: %s", missing_sensor_ids)

    return readings


def _get_sensors(zipcode: str) -> typing.List[Sensor]:
    distances = _get_distances(zipcode)
    readings = _get_readings(distances.keys())
    return sorted(
        [
            Sensor(sensor_id, distances[sensor_id], pm25)
            for sensor_id, pm25 in readings.items()
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
