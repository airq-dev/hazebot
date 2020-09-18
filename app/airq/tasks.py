import datetime

from airq.celery import celery
from airq.lib.logging import get_airq_logger


logger = get_airq_logger(__name__)


@celery.task()
def models_sync():
    from airq.sync import models_sync

    models_sync()


@celery.task()
def bulk_send(message: str, last_active_at: float):
    from airq.models.clients import Client

    num_sent = 0
    for client in Client.query.filter_inactive_since(last_active_at).all():
        try:
            if client.send_message(message):
                num_sent += 1
        except Exception as e:
            logger.exception("Failed to send message to %s: %s", client, e)

    logger.info("Sent %s messages", num_sent)
