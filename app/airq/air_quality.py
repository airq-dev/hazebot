import collections
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


DEAD_SENSOR_CACHE: cache.Cache[int, bool] = cache.Cache(
    prefix="purpleair-pm25-sensor-dead-", timeout=60 * 60
)


PM25_CACHE: cache.Cache[int, float] = cache.Cache(
    prefix="purpleair-pm25-sensor-reading-", timeout=60 * 10
)


SENSOR_DISTANCE_CACHE: cache.Cache[
    str, "collections.OrderedDict[int, float]"
] = cache.Cache(prefix="purpleair-sensor-distance", timeout=24 * 60 * 60)


@dataclasses.dataclass(frozen=True)
class Metrics:
    pm25: float
    num_sensors: int
    max_sensor_distance: float
    readings: typing.List[float]

    @property
    def pm25_display(self) -> str:
        return util.get_pm25_display(self.pm25)


@dataclasses.dataclass(frozen=True)
class Sensor:
    id: int
    distance: float
    pm25: float


def _get_sensor_distances(
    zipcode: str,
) -> "collections.OrderedDict[int, float]":  # See https://stackoverflow.com/a/52626233

    #
    # This is an OrderedDict from sensor ids to their distance from this zip.
    # We exclude them if they're "dead"; that is, not returning a valid reading.
    # If we do have dead sensors, we query the DB for other nearby sensors
    # so that we can (hopefully) find 10 active nearby sensors to read from.
    #

    sensor_to_distance: "collections.OrderedDict[int, float]" = SENSOR_DISTANCE_CACHE.get(
        zipcode, collections.OrderedDict()
    )

    exclude = set(sensor_to_distance)
    for sensor_id in exclude:
        if DEAD_SENSOR_CACHE.get(sensor_id):
            del sensor_to_distance[sensor_id]

    num_missing = DESIRED_NUM_SENSORS - len(sensor_to_distance)
    if num_missing:
        sensor_to_distance.update(
            geodb.get_sensor_distances(zipcode, exclude, num_missing, MAX_SENSOR_RADIUS)
        )
        SENSOR_DISTANCE_CACHE.set(zipcode, sensor_to_distance)

    return sensor_to_distance


def _get_sensors(zipcode: str) -> typing.List[Sensor]:
    sensor_to_distance = _get_sensor_distances(zipcode)

    # Get a list of sensors for which we already have good pm25 data.
    # We won't be needing to get these from the cache.
    sensors = []
    for sensor_id, distance in list(sensor_to_distance.items()):
        pm25 = PM25_CACHE.get(sensor_id)
        if pm25:
            sensors.append(Sensor(sensor_id, distance, pm25))
            del sensor_to_distance[sensor_id]

    if sensor_to_distance:
        try:
            readings = purpleair.get_readings(set(sensor_to_distance))
        except purpleair.ApiException as e:
            logger.exception(
                "Error retrieving data for sensors %s and zipcode %s: %s",
                set(sensor_to_distance),
                zipcode,
                e,
            )
        else:
            for sensor_id, pm25 in readings.items():
                if pm25 <= 0 or pm25 > 500:
                    logger.warning(
                        "Marking sensor %s dead because its pm25 is %s",
                        sensor_id,
                        pm25,
                    )
                    DEAD_SENSOR_CACHE.set(sensor_id, True)
                else:
                    distance = sensor_to_distance.pop(sensor_id)
                    PM25_CACHE.set(sensor_id, pm25)
                    sensors.append(Sensor(sensor_id, distance, pm25))

    # This should be empty now if we've gotten pm25 info for every sensor.
    if sensor_to_distance:
        logger.warning("No results for ids: %s", set(sensor_to_distance))

    return sorted(sensors, key=lambda s: s.distance)


def get_metrics(zipcode: str) -> typing.Optional[Metrics]:
    sensors = _get_sensors(zipcode)
    if not sensors:
        return None

    average_pm25 = round(sum(s.pm25 for s in sensors) / len(sensors), ndigits=3)

    return Metrics(
        pm25=average_pm25,
        num_sensors=len(sensors),
        max_sensor_distance=round(sensors[-1].distance, ndigits=3),
        readings=[round(s.pm25, ndigits=3) for s in sensors],
    )
