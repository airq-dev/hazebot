import textwrap
import time

from sqlalchemy import text

from airq.celery import get_celery_logger
from airq.config import db
from airq.lib.clock import now
from airq.lib.util import chunk_list
from airq.models.zipcodes import Zipcode

# Try to get at least 8 readings per zipcode.
DESIRED_NUM_READINGS = 8

# Allow any number of readings within 2.5km from the zipcode centroid.
DESIRED_READING_DISTANCE_KM = 2.5


def update():
    logger = get_celery_logger()

    ts = now()
    start_ts = time.perf_counter()

    # This approach is really slow (about 5 mins) and hard to test
    # since it's so complex. How can we make this better?
    #
    # For testability: it would be useful to test this in a single 
    # zipcode containing a few sensors. That would allow us to assert
    # that the algorithm works correctly:
    # - When there are two equidistant sensors, it assigns equal weight to each.
    # - When there are two sensors which are not equidistant, the one closer
    #   to the origin gets more weight.
    # - When there are three equidistant sensors, it assigns equal weight to each.
    # - When there are three sensors which are not equidistant, the closer
    #   sensors are assigned more weight.
    #

    sql = text(
        textwrap.dedent(
            f"""
    -- Compute the Voronoi Diagram for the set of sensors
    WITH voronoi_cells AS (
        SELECT
            ST_Intersection(
                (ST_DUMP(
                    ST_VoronoiPolygons(
                        ST_Collect(coordinates)
                    ) 
                )).geom,
                ST_MakeEnvelope(-180, -90, 180, 90)
            ) as cell
        FROM sensors
        WHERE coordinates IS NOT NULL
        AND updated_at > :updated_at
    ),

    -- Map each Voronoi cell to the sensor it contains
    sensors_with_cells AS (
        SELECT 
            s.id,
            s.latest_reading,
            s.humidity,
            s.pm_cf_1,
            ST_Area(v.cell) as area
        FROM sensors s
        JOIN voronoi_cells v
        ON ST_Within(s.coordinates, v.cell)
    ),

    -- Find the distance of the eighth closest sensor to each zipcode
    zipcodes_to_distance AS (
        SELECT
            z.id,
            (
                SELECT sz.distance
                FROM sensors_zipcodes sz
                WHERE sz.zipcode_id = z.id
                ORDER BY sz.distance
                LIMIT 1
                OFFSET :desired_num_readings
            ) as distance_to_eighth_closest_sensor
        FROM zipcodes z
        GROUP BY z.id
    ) 

    -- For each zipcode, compute metrics
    SELECT
        zd.id,
        SUM(sc.latest_reading * sc.area) / SUM(sc.area) as pm25,
        SUM(sc.humidity * sc.area) / SUM(sc.area) as humidity,
        SUM(sc.pm_cf_1 * sc.area) / SUM(sc.area) as pm_cf_1,
        MAX(sz.distance) AS max_distance,
        MIN(sz.distance) AS min_distance,
        COUNT(sc.id) AS num_sensors,
        ARRAY_AGG(sc.id) AS sensor_ids
    FROM zipcodes_to_distance zd
    JOIN sensors_zipcodes sz
    ON sz.zipcode_id = zd.id
    JOIN sensors_with_cells sc
    ON sc.id = sz.sensor_id

    -- Include all sensors within 2.5 KM of the zipcode's
    -- centroid. If there are fewer than 8 sensors within
    -- 2.5 KM, include the closest eight sensors.
    WHERE sz.distance <= GREATEST(zd.distance_to_eighth_closest_sensor, :desired_reading_distance_km)

    GROUP BY zd.id
    """
        )
    )

    rows = list(db.engine.execute(
        sql,
        {
            "desired_num_readings": DESIRED_NUM_READINGS - 1,
            "desired_reading_distance_km": DESIRED_READING_DISTANCE_KM,
            "updated_at": ts.timestamp() - (30 * 60),
        },
    ))

    end_ts = time.perf_counter()
    duration = end_ts - start_ts
    logger.info("executed sql in %f seconds", duration)

    updates = []
    for row in rows:
        (
            zipcode_id,
            pm25,
            humidity,
            pm_cf_1,
            max_sensor_distance,
            min_sensor_distance,
            num_sensors,
            sensor_ids,
        ) = row

        details = {
            "num_sensors": num_sensors,
            "min_sensor_distance": min_sensor_distance,
            "max_sensor_distance": max_sensor_distance,
            "sensor_ids": sensor_ids,
        }

        updates.append(
            {
                "id": zipcode_id,
                "pm25": round(pm25, ndigits=3),
                "humidity": round(humidity, ndigits=3),
                "pm_cf_1": round(pm_cf_1, ndigits=3),
                "pm25_updated_at": ts.timestamp(),
                "metrics_data": details,
            }
        )

    logger.info("Updating %d zipcodes", len(updates))
    for mappings in chunk_list(updates, batch_size=5000):
        db.session.bulk_update_mappings(Zipcode, mappings)
        db.session.commit()
