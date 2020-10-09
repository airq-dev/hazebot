from flask_babel import force_locale
from flask_babel import gettext

from airq import config
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


@celery.task()
def send_intro_message(client_id: int):
    from airq.models.clients import Client

    client = Client.query.filter_by(id=client_id).first()
    if client is None:
        logger.exception("Couldn't find client with id %s", client_id)
        return

    with force_locale(client.locale):
        message = gettext(
            'Thanks for texting Hazebot! You\'ll receive timely texts when AQI in your area changes based on PurpleAir data. Text Menu ("M") for more features including recommendations, or end alerts by texting ("E").\n\nSave this contact and text your zipcode anytime for an AQI update.'
        )
        media = f"{config.SERVER_URL}/vcard/{client.locale}.vcf"
        client.send_message(message, media=media)
