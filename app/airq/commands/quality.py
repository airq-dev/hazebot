import collections
import dataclasses
import datetime
import enum
import logging
import typing

from sqlalchemy import and_
from sqlalchemy import func

from airq.commands.base import ApiCommandHandler
from airq.lib.geo import haversine_distance
from airq.lib.readings import Pm25
from airq.lib.readings import pm25_to_aqi
from airq.models.cities import City
from airq.models.clients import Client
from airq.models.metrics import Metric
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


@dataclasses.dataclass
class AirQualityMetrics:
    zipcode: str
    city_name: str
    distance: str
    average_pm25: float
    num_readings: int

    @property
    def pm25_level(self) -> Pm25:
        return Pm25.from_measurement(self.average_pm25)


class GetQualityHandler(ApiCommandHandler):
    class Mode(enum.Enum):
        DEFAULT = 0  # Just show short info about the zipcode.
        DETAILS = 1  # Show detailed info about the zipcode and recommendations.
        RECOMMEND = 2  # Just show recommendations

    def __init__(self, *args, mode: Mode = Mode.DEFAULT):
        super().__init__(*args)
        self.mode = mode

    @property
    def recommend(self) -> bool:
        return self.mode in (self.Mode.DETAILS, self.Mode.RECOMMEND)

    @property
    def recommend_only(self) -> bool:
        return self.mode == self.Mode.RECOMMEND

    def handle(self, zipcode: typing.Optional[str] = None) -> typing.List[str]:
        aqi_metrics = {}
        target_metrics = {}

        if zipcode is None:
            zipcode = self.client.get_last_requested_zipcode()
            if zipcode is None:
                return [
                    "Looks like you haven't use hazebot before! Please text us a zipcode and we'll send you the air quality"
                ]
            else:
                raw_zipcode = zipcode.zipcode
        else:
            raw_zipcode = zipcode
            zipcode = Zipcode.get_by_zipcode(zipcode)

        if zipcode:
            aqi_metrics = self._get_air_quality_metrics(zipcode)
            target_metrics = aqi_metrics.get(zipcode.id)

        if not target_metrics:
            return [
                f'Oops! We couldn\'t determine the air quality for "{raw_zipcode}". Please try a different zip code.'
            ]

        message = []

        if not self.recommend_only:
            # We're either in details or default mode
            aqi = pm25_to_aqi(target_metrics.average_pm25)
            message.append(
                "Air quality near {} {} is {}{}.".format(
                    target_metrics.city_name,
                    zipcode.zipcode,
                    target_metrics.pm25_level.display.upper(),
                    f" (AQI: {aqi})" if aqi else "",
                )
            )

        if self.recommend:
            # We're either in details or recommend mode
            recommendations = self._get_recommendations(
                aqi_metrics.values(), target_metrics.zipcode, target_metrics.pm25_level
            )
            if recommendations:
                if message:
                    message.append(
                        ""
                    )  # Add a newline if we have other text to display.
                message.extend(recommendations)
            elif self.recommend_only:
                # We couldn't find any recommendations, so display a nice message since we're also
                # not showing any info about the zipcode.
                msg = "We couldn't find any zipcodes near {} with better air quality than {}.".format(
                    zipcode.zipcode, target_metrics.pm25_level.display,
                )
                if target_metrics.pm25_level >= Pm25.UNHEALTHY:
                    msg += " Time to stay inside!"
                message.append(msg)

        if self.mode == self.Mode.DETAILS:
            message.append("")
            message.append(
                f"Average PM2.5 from {target_metrics.num_readings} sensor(s) near {zipcode.zipcode} is {target_metrics.average_pm25} µg/m³."
            )

        message.append("")
        message.extend(self._get_menu())

        self.client.log_request(zipcode)

        return message

    def _get_recommendations(
        self, metrics: typing.Iterable[AirQualityMetrics], zipcode: str, pm25_cutoff: Pm25
    ) -> typing.List[str]:
        message = []
        num_desired = 5
        lower_pm25_metrics = sorted(
            [m for m in metrics if m.zipcode != zipcode and m.pm25_level < pm25_cutoff],
            # Sort by pm25 level, and then by distance from the desired zip to break ties
            key=lambda m: (m.pm25_level, m.distance),
        )[:num_desired]
        if lower_pm25_metrics:
            message.append("Try these other places near you for better air quality:")
            for m in lower_pm25_metrics:
                message.append(
                    " - {} {}: {}".format(m.city_name, m.zipcode, m.pm25_level.display)
                )
        return message

    def _get_air_quality_metrics(self, zipcode: Zipcode) -> typing.Dict[int, AirQualityMetrics]:
        # Get a all zipcodes (inclusive) within 25km
        logger.info("Retrieving metrics for zipcode %s", zipcode.zipcode)
        if self.recommend:
            zipcodes_map = self._get_nearby_zipcodes(zipcode)
        else:
            zipcodes_map = {}
            zipcodes_map[zipcode.id] = 0
        return self._get_air_quality_metrics_for_zipcodes(zipcodes_map)

    def _get_nearby_zipcodes(
        self, zipcode: Zipcode
    ) -> typing.Dict[int, float]:
        zipcodes_map: typing.Dict[int, float] = {}
        zipcodes_map[zipcode.id] = 0

        gh = list(zipcode.geohash)
        while gh:
            query = Zipcode.query.with_entities(
                Zipcode.id,
                Zipcode.latitude,
                Zipcode.longitude,
            )
            for i, c in enumerate(gh, start=1):
                col = getattr(Zipcode, f"geohash_bit_{i}")
                query = query.filter(col == c)
            if zipcodes_map:
                query = query.filter(~Zipcode.id.in_(zipcodes_map.keys()))
            for zipcode_id, distance in sorted(
                [
                    (
                        r[0],
                        haversine_distance(r[2], r[1], zipcode.longitude, zipcode.latitude,),
                    )
                    for r in query.all()
                ],
                key=lambda t: t[1],
            ):
                if distance <= MAX_NEARBY_ZIPCODE_RADIUS_KM:
                    zipcodes_map[zipcode_id] = distance
                if len(zipcodes_map) >= MAX_NUM_NEARBY_ZIPCODES:
                    return zipcodes_map
            gh.pop()

        return zipcodes_map

    def _get_air_quality_metrics_for_zipcodes(
        self,
        zipcodes_map: typing.Dict[int, float]
    ) -> typing.Dict[int, AirQualityMetrics]:
        subquery = Metric.query.with_entities(
            Metric.zipcode_id, 
            func.max(Metric.timestamp).label('max_ts')
        ).group_by(Metric.zipcode_id).subquery('max_ts')

        query = Metric.query.join(
            subquery,
            and_(Metric.zipcode_id == subquery.c.zipcode_id, Metric.timestamp == subquery.c.max_ts)
        ).join(
            Zipcode
        ).join(
            City
        ).filter(
            Zipcode.id.in_(zipcodes_map.keys())
        ).with_entities(
            Metric.zipcode_id,
            Metric.value,
            Metric.num_sensors,
            Zipcode.zipcode,
            City.name
        )

        aqi_metrics = {}
        for zipcode_id, pm25, num_sensors, zipcode, city_name in query.all():
            aqi_metrics[zipcode_id] = AirQualityMetrics(
                zipcode=zipcode,
                city_name=city_name,
                distance=zipcodes_map[zipcode_id],
                average_pm25=pm25,
                num_readings=num_sensors
            )

        return aqi_metrics
