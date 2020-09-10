import dataclasses
import logging
import typing

from airq import geodb
from airq import purpleair
from airq import util
from airq.models.sensors import get_sensor_reading_map


logger = logging.getLogger(__name__)


# Try to get at least 10 readings per zipcode.
DESIRED_NUM_READINGS = 10

# Allow any number of readings within 5km from the zipcode centroid.
DESIRED_READING_DISTANCE_KM = 5

# Get readings for zipcodes within 150 mi of the target zipcode.
MAX_NEARBY_ZIPCODE_RADIUS_KM = 150

# Try to get readings for up to 200 zipcodes near the target zipcode.
MAX_NUM_NEARBY_ZIPCODES = 200


@dataclasses.dataclass(frozen=True)
class Metrics:
    zipcode: str
    city_name: str
    average_pm25: float
    num_readings: int
    closest_reading: float
    farthest_reading: float
    distance: float
    readings: typing.List[float]

    @property
    def pm25_level(self) -> util.PM25:
        return util.PM25.from_measurement(self.average_pm25)


def get_metrics_for_zipcode(target_zipcode: str) -> typing.Dict[str, Metrics]:
    # Get a all zipcodes (inclusive) within 25km
    logger.info("Retrieving metrics for zipcode %s", target_zipcode)
    zipcodes = geodb.get_nearby_zipcodes(
        target_zipcode,
        max_radius=MAX_NEARBY_ZIPCODE_RADIUS_KM,
        num_desired=MAX_NUM_NEARBY_ZIPCODES,
    )

    # Get the cities each of these zipcodes are in
    city_names = geodb.get_city_names(
        {zipcode.city_id for zipcode in zipcodes.values()}
    )

    # Now get all sensors for each of these zipcodes
    logger.info("Retrieving sensors for %s zipcodes", len(zipcodes))
    zipcodes_to_sensors = geodb.get_sensors_for_zipcodes(set(zipcodes))
    sensor_ids: typing.Set[int] = set()
    for sensors in zipcodes_to_sensors.values():
        for sensor in sensors:
            sensor_ids.add(sensor.sensor_id)

    logger.info("Retrieving readings for %s sensors", len(sensor_ids))
    pm25_readings = {}
    # pm25_readings = get_sensor_reading_map(sensor_ids)
    # sensor_ids -= pm25_readings.keys()

    # If we failed to get some readings from postgres, fall back to making a live query.
    if sensor_ids:
        logger.info(
            "Retrieving readings for %s sensors from purpleair", len(sensor_ids)
        )
        pm25_readings.update(purpleair.get_pm25_readings(sensor_ids))

    # Now construct our metrics
    logger.info("Constructing metrics from %s readings", len(pm25_readings))
    metrics = {}
    for zipcode_id, sensors in zipcodes_to_sensors.items():
        readings = []
        closest_reading = float("inf")
        farthest_reading = 0.0
        for sensor in sorted(sensors, key=lambda s: s.distance):
            pm25 = pm25_readings.get(sensor.sensor_id)
            if pm25:
                if (
                    len(pm25_readings) < DESIRED_NUM_READINGS
                    or sensor.distance < DESIRED_READING_DISTANCE_KM
                ):
                    readings.append(pm25)
                    closest_reading = min(sensor.distance, closest_reading)
                    farthest_reading = max(sensor.distance, farthest_reading)
                else:
                    break

        if readings:
            zipcode, city_id, distance = zipcodes[zipcode_id]
            metrics[zipcode] = Metrics(
                zipcode=zipcode,
                city_name=city_names[city_id],
                average_pm25=round(sum(readings) / len(readings), ndigits=3),
                num_readings=len(readings),
                closest_reading=round(closest_reading, ndigits=3),
                farthest_reading=round(farthest_reading, ndigits=3),
                distance=round(distance, ndigits=3),
                readings=readings,
            )

    return metrics
