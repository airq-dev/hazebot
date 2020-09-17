from airq.celery import celery


@celery.task()
def models_sync():
    from airq.sync import models_sync

    models_sync()
