from airq.celery import celery


@celery.task()
def models_sync():
    from airq.sync import models_sync

    models_sync()


## REMOVE CODE BELOW THIS ##


@celery.task()
def throw_in_celery():
    from airq.sync import test_me

    test_me()
