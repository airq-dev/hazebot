import typing

from airq.celery import celery
from airq.lib.logging import get_airq_logger


logger = get_airq_logger(__name__)


@celery.task()
def models_sync():
    from airq.sync import models_sync

    models_sync()


@celery.task()
def bulk_send(message: str, last_active_at: float, locale: str, test_phone_number: typing.Optional[str] = None):
    from airq.models.clients import Client
    from airq.lib.sms import coerce_phone_number

    if test_phone_number:
        test_phone_number = coerce_phone_number(test_phone_number)

    num_sent = 0
    for client in Client.query.filter_inactive_since(last_active_at).all():
        if test_phone_number and test_phone_number != client.identifier:
            continue

        if client.locale != locale:
            continue

        try:
            if client.send_message(message):
                num_sent += 1
        except Exception as e:
            logger.exception("Failed to send message to %s: %s", client, e)

    logger.info("Sent %s messages", num_sent)
