import datetime
import requests

from airq.celery import celery
from airq.celery import get_celery_logger


@celery.task()
def update_sensor_readings():
    from airq.models import sensors

    logger = get_celery_logger()
    logger.info("Fetching sensor readings from purpleair")

    try:
        resp = requests.get("https://www.purpleair.com/json")
        resp.raise_for_status()
    except requests.RequestException:
        logger.exception("Error updating purpleair data")
        results = []
    else:
        results = resp.json().get("results", [])

    logger.info("Recieved %s readings", len(results))

    sensor_readings = []
    for i, result in enumerate(results):
        if i % 100 == 0:
            logger.info("Processed %s of %s readings", i, len(results))

        if sensors.is_valid_reading(result):
            pm25 = float(result["PM2_5Value"])
            sensor_readings.append(
                {"id": result["ID"], "updated_at": result["LastSeen"], "reading": pm25}
            )

    logger.info("Inserting %s new readings", len(sensor_readings))
    sensors.upsert_sensor_readings(sensor_readings)
