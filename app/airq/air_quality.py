import typing

from airq import geodb
from airq import purpleair


DESIRED_NUM_SENSORS = 10


MAX_SENSOR_RADIUS = 25


def get_metrics_for_zipcode(
    zipcode: str,
) -> typing.Dict[str, typing.Dict[str, typing.Union[float, int]]]:
    # Get a all zipcodes (inclusive) within 25km
    zipcodes = geodb.get_nearby_zipcodes(zipcode, MAX_SENSOR_RADIUS)

    # Now get all sensors for each of these zipcodes
    zipcodes_to_sensors = geodb.get_sensors_for_zipcodes(set(zipcodes))

    # Now get the pm25 readings for all present sensors
    sensor_ids: typing.Set[int] = set()
    for sensors in zipcodes_to_sensors.values():
        for sensor_id, _ in sensors:
            sensor_ids.add(sensor_id)
    pm25_readings = purpleair.get_pm25_readings(sensor_ids)

    # Now construct our metrics
    metrics = {}
    for zipcode_id, sensors in zipcodes_to_sensors.items():
        nearby_readings = []
        distances = []
        for sensor_id, distance in sorted(sensors, key=lambda s: s[1]):
            pm25 = pm25_readings.get(sensor_id)
            if pm25:
                # Try to find at least 5 readings within 5km
                if len(pm25_readings) < DESIRED_NUM_SENSORS or distance < 5:
                    nearby_readings.append(pm25)
                    distances.append(distance)
        if nearby_readings:
            zipcode, distance = zipcodes[zipcode_id]
            metrics[zipcode] = {
                "avg_pm25": round(
                    sum(nearby_readings) / len(nearby_readings), ndigits=3
                ),
                "num_readings": len(nearby_readings),
                "closest_reading": distances[0],
                "farthest_reading": distances[-1],
                "distance": round(distance, ndigits=3),
            }

    return metrics
