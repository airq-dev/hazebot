import collections
import dataclasses
import datetime
import logging
import typing

from airq.lib.geo import haversine_distance
from airq.lib.readings import Pm25
from airq.models.cities import City
from airq.models.relations import SensorZipcodeRelation
from airq.models.sensors import Sensor
from airq.models.zipcodes import Zipcode


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
    def pm25_level(self) -> Pm25:
        return Pm25.from_measurement(self.average_pm25)


def _get_nearby_zipcodes(
    zipcode: str,
) -> typing.Dict[int, typing.Tuple[str, str, float]]:
    zipcodes: typing.Dict[int, typing.Tuple[str, str, float]] = {}
    obj = Zipcode.query.filter_by(zipcode=zipcode).first()
    if not obj:
        return zipcodes

    zipcodes[obj.id] = (obj.zipcode, obj.city.name, 0)
    gh = list(obj.geohash)

    while gh:
        query = Zipcode.query.with_entities(
            Zipcode.id, Zipcode.zipcode, City.name, Zipcode.latitude, Zipcode.longitude
        ).join(City)
        for i, c in enumerate(gh, start=1):
            col = getattr(Zipcode, f"geohash_bit_{i}")
            query = query.filter(col == c)
        if zipcodes:
            query = query.filter(~Zipcode.id.in_(zipcodes.keys()))
        for zipcode_id, zipcode, city_name, distance in sorted(
            [
                (
                    r[0],
                    r[1],
                    r[2],
                    haversine_distance(r[4], r[3], obj.longitude, obj.latitude,),
                )
                for r in query.all()
            ],
            key=lambda t: t[3],
        ):
            if distance <= MAX_NEARBY_ZIPCODE_RADIUS_KM:
                zipcodes[zipcode_id] = (zipcode, city_name, distance)
            if len(zipcodes) >= MAX_NUM_NEARBY_ZIPCODES:
                return zipcodes
        gh.pop()

    return zipcodes


def _build_zipcodes_to_sensors_map(
    zipcode_ids: typing.Set[int],
) -> typing.Tuple[typing.Dict[int, typing.List[typing.Tuple[float, float]]], int]:
    num_readings = 0
    cutoff = datetime.datetime.now().timestamp() - (60 * 60)
    zipcodes_to_sensors: typing.Dict[
        int, typing.List[typing.Tuple[float, float]]
    ] = collections.defaultdict(list)
    for zipcode_id, latest_reading, distance in (
        SensorZipcodeRelation.query.join(Sensor)
        .with_entities(
            SensorZipcodeRelation.zipcode_id,
            Sensor.latest_reading,
            SensorZipcodeRelation.distance,
        )
        .filter(SensorZipcodeRelation.zipcode_id.in_(zipcode_ids))
        .filter(Sensor.updated_at > cutoff)
    ):
        num_readings += 1
        zipcodes_to_sensors[zipcode_id].append((latest_reading, distance))

    return zipcodes_to_sensors, num_readings


def _construct_metrics(
    zipcodes_to_sensors: typing.Dict[int, typing.List[typing.Tuple[float, float]]],
    zipcodes_map: typing.Dict[int, typing.Tuple[str, str, float]],
) -> typing.Dict[str, Metrics]:
    metrics = {}
    for zipcode_id, sensor_tuples in zipcodes_to_sensors.items():
        readings: typing.List[float] = []
        closest_reading = float("inf")
        farthest_reading = 0.0
        for reading, distance in sorted(sensor_tuples, key=lambda s: s[1]):
            if (
                len(readings) < DESIRED_NUM_READINGS
                or distance < DESIRED_READING_DISTANCE_KM
            ):
                readings.append(reading)
                closest_reading = min(distance, closest_reading)
                farthest_reading = max(distance, farthest_reading)
            else:
                break

        if readings:
            zipcode, city_name, distance = zipcodes_map[zipcode_id]
            metrics[zipcode] = Metrics(
                zipcode=zipcode,
                city_name=city_name,
                average_pm25=round(sum(readings) / len(readings), ndigits=3),
                num_readings=len(readings),
                closest_reading=round(closest_reading, ndigits=3),
                farthest_reading=round(farthest_reading, ndigits=3),
                distance=round(distance, ndigits=3),
                readings=readings,
            )

    return metrics


def get_metrics_for_zipcode(target_zipcode: str) -> typing.Dict[str, Metrics]:
    # Get a all zipcodes (inclusive) within 25km
    logger.info("Retrieving metrics for zipcode %s", target_zipcode)
    zipcodes_map = _get_nearby_zipcodes(target_zipcode)
    zipcodes_to_sensors, num_readings = _build_zipcodes_to_sensors_map(
        set(zipcodes_map)
    )

    # Now construct our metrics
    logger.info("Constructing metrics from %s readings", num_readings)
    return _construct_metrics(zipcodes_to_sensors, zipcodes_map)
