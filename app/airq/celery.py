from celery import Celery
from celery import signals
from celery.schedules import crontab
from kombu.utils.url import safequote

from airq import settings


BEAT_SCHEDULE = {
    "models_sync": {
        "task": "airq.tasks.models_sync",
        "schedule": crontab(minute="*/10"),
    }
}


def get_celery_logger():
    from celery.utils.log import get_task_logger

    return get_task_logger(__name__)


celery = Celery(settings.app.import_name)
celery.conf.update(
    accept_content=["application/json"],
    beat_schedule=BEAT_SCHEDULE,
    broker_url="sqs://{}:{}@".format(
        safequote(settings.AWS_ACCESS_KEY_ID), safequote(settings.AWS_SECRET_ACCESS_KEY)
    ),
    broker_transport_options={"region": "us-west-1"},
    result_serializer="json",
    task_default_queue=f"celery-{settings.FLASK_ENV}",
    task_serializer="json",
    worker_enable_remote_control=False,
    worker_hijack_root_logger=False,
)
celery.conf.update(settings.app.config)


class ContextTask(celery.Task):  # type: ignore
    def __call__(self, *args, **kwargs):
        with settings.app.app_context():
            return self.run(*args, **kwargs)

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        get_celery_logger().exception(
            "%s: %s", type(exc).__name__, str(exc), exc_info=exc
        )
        super().on_failure(exc, task_id, args, kwargs, einfo)


celery.Task = ContextTask


@signals.setup_logging.connect
def setup_celery_logging(**kwargs):
    dictConfig(settings.LOGGING_CONFIG)


celery.autodiscover_tasks(["airq"])
