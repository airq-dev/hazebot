from celery import Celery
from celery import signals
from celery.schedules import crontab
from kombu.utils.url import safequote

from airq import config


BEAT_SCHEDULE = {
    "models_sync": {
        "task": "airq.tasks.models_sync",
        "schedule": crontab(minute="*/10"),
    }
}


def get_celery_logger():
    from celery.utils.log import get_task_logger

    return get_task_logger(__name__)


if config.FLASK_ENV == "development":
    # Use redis in dev so that people don't need to setup AWS credentials.
    broker_url = "redis://redis:6379/0"
    transport_options = {}
else:
    broker_url = "sqs://{}:{}@".format(
        safequote(config.AWS_ACCESS_KEY_ID), safequote(config.AWS_SECRET_ACCESS_KEY)
    )
    transport_options = {"region": "us-west-1"}


celery = Celery(config.app.import_name)
celery.conf.update(
    accept_content=["application/json"],
    beat_schedule=BEAT_SCHEDULE,
    broker_url=broker_url,
    broker_transport_options=transport_options,
    result_serializer="json",
    task_default_queue=f"celery-{config.FLASK_ENV}",
    task_serializer="json",
    worker_enable_remote_control=False,
    worker_hijack_root_logger=False,
)
celery.conf.update(config.app.config)


class ContextTask(celery.Task):  # type: ignore
    def __call__(self, *args, **kwargs):
        with config.app.app_context():
            return self.run(*args, **kwargs)

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        get_celery_logger().exception(
            "%s: %s", type(exc).__name__, str(exc), exc_info=exc
        )
        from airq.lib.logging import handle_exc
        handle_exc(exc)
        super().on_failure(exc, task_id, args, kwargs, einfo)


celery.Task = ContextTask


@signals.setup_logging.connect
def setup_celery_logging(**kwargs):
    dictConfig(config.LOGGING_CONFIG)


celery.autodiscover_tasks(["airq"])
