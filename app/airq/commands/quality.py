import collections
import dataclasses
import datetime
import enum
import logging
import typing

from airq.commands.base import ApiCommand
from airq.commands.base import CommandContext
from airq.lib.geo import haversine_distance
from airq.lib.readings import Pm25
from airq.lib.readings import pm25_to_aqi
from airq.models.cities import City
from airq.models.requests import Request
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


class GetQualityMode(enum.Enum):
    DEFAULT = 0  # Just show short info about the zipcode.
    DETAILS = 1  # Show detailed info about the zipcode and recommendations.
    RECOMMEND = 2  # Just show recommendations


class GetQuality(ApiCommand):
    def __init__(self, zipcode: str, mode: GetQualityMode, *args):
        super().__init__(*args)
        self.zipcode = zipcode
        self.mode = mode

    @classmethod
    def parse(cls, ctx: CommandContext) -> typing.Optional["ApiCommand"]:
        user_input = ctx.user_input.split()
        mode = GetQualityMode.DEFAULT
        directives = ("l", "d", "r")
        if user_input[0].lower() in directives:
            directive = user_input.pop(0).lower()

            if directive == "d":
                mode = GetQualityMode.DETAILS
            if directive == "r":
                mode = GetQualityMode.RECOMMEND

            if not user_input:
                repeat = True
            else:
                repeat = directive == "l"

            if repeat:
                zipcode = ctx.client.get_last_requested_zipcode()
                if zipcode:
                    user_input.append(zipcode)

        if len(user_input) == 1 and len(user_input[0]) == 5 and user_input[0].isdigit():
            return cls(user_input[0], mode, ctx)

        return None

    @property
    def recommend(self) -> bool:
        return self.mode in (GetQualityMode.DETAILS, GetQualityMode.RECOMMEND)

    @property
    def recommend_only(self) -> bool:
        return self.mode == GetQualityMode.RECOMMEND

    def handle(self) -> typing.List[str]:
        metrics = self._get_metrics()
        target_metrics = metrics.get(self.zipcode)
        if not target_metrics:
            return [
                f'Oops! We couldn\'t determine the air quality for "{self.zipcode}". Please try a different zip code.'
            ]
        else:
            message = []

            if not self.recommend_only:
                # We're either in details or default mode
                aqi = pm25_to_aqi(target_metrics.average_pm25)
                message.append(
                    "Air quality near {} {} is {}{}.".format(
                        target_metrics.city_name,
                        self.zipcode,
                        target_metrics.pm25_level.display.upper(),
                        f" (AQI: {aqi})" if aqi else "",
                    )
                )

            if self.recommend:
                # We're either in details or recommend mode
                recommendations = self._get_recommendations(
                    metrics.values(), target_metrics.pm25_level
                )
                if not recommendations and self.recommend_only:
                    # We couldn't find any recommendations, so display a nice message since we're also
                    # not showing any info about the zipcode.
                    msg = "We couldn't find any zipcodes near {} with better air quality than {}.".format(
                        self.zipcode, target_metrics.pm25_level.display,
                    )
                    if target_metrics.pm25_level >= Pm25.UNHEALTHY:
                        msg += " Time to stay inside!"
                    message.append(msg)
                else:
                    message.extend(recommendations)

            if self.mode == GetQualityMode.DETAILS:
                message.append("")
                message.append(
                    f"Average PM2.5 from {target_metrics.num_readings} sensor(s) near {self.zipcode} is {target_metrics.average_pm25} micrograms/m^3."
                )

            message.append("")
            message.extend(self._get_menu())

            self.ctx.client.log_request(self.zipcode)

            return message

    def _get_recommendations(
        self, metrics: typing.Iterable[Metrics], pm25_cutoff: Pm25
    ) -> typing.List[str]:
        message = []
        num_desired = 5
        lower_pm25_metrics = sorted(
            [
                m
                for m in metrics
                if m.zipcode != self.zipcode and m.pm25_level < pm25_cutoff
            ],
            # Sort by pm25 level, and then by distance from the desired zip to break ties
            key=lambda m: (m.pm25_level, m.distance),
        )[:num_desired]
        if lower_pm25_metrics:
            message.append("")
            message.append("Try these other places near you for better air quality:")
            for m in lower_pm25_metrics:
                message.append(
                    " - {} {}: {}".format(m.city_name, m.zipcode, m.pm25_level.display)
                )
        return message

    def _get_metrics(self) -> typing.Dict[str, Metrics]:
        # Get a all zipcodes (inclusive) within 25km
        logger.info("Retrieving metrics for zipcode %s", self.zipcode)
        if self.recommend:
            zipcodes_map = self._get_nearby_zipcodes()
        else:
            zipcodes_map = {}
            obj = Zipcode.get_by_zipcode(self.zipcode)
            if obj:
                zipcodes_map[obj.id] = (obj.zipcode, obj.city.name, 0)

        zipcodes_to_sensors, num_readings = self._build_zipcodes_to_sensors_map(
            set(zipcodes_map)
        )

        # Now construct our metrics
        logger.info("Constructing metrics from %s readings", num_readings)
        return self._construct_metrics(zipcodes_to_sensors, zipcodes_map)

    def _get_nearby_zipcodes(self) -> typing.Dict[int, typing.Tuple[str, str, float]]:
        zipcodes: typing.Dict[int, typing.Tuple[str, str, float]] = {}
        obj = Zipcode.get_by_zipcode(self.zipcode)
        if not obj:
            return zipcodes

        zipcodes[obj.id] = (obj.zipcode, obj.city.name, 0)
        gh = list(obj.geohash)

        while gh:
            query = Zipcode.query.with_entities(
                Zipcode.id,
                Zipcode.zipcode,
                City.name,
                Zipcode.latitude,
                Zipcode.longitude,
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
        self, zipcode_ids: typing.Set[int],
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
        self,
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
