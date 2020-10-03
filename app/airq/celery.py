import os

import flask
from celery import Celery
from celery import signals
from celery.schedules import crontab
from kombu.utils.url import safequote

from airq import config


BEAT_SCHEDULE = {}

if not config.TESTING:
    BEAT_SCHEDULE["models_sync"] = {
        "task": "airq.tasks.models_sync",
        "schedule": crontab(minute="*/10"),
    }


def get_celery_logger():
    from celery.utils.log import get_task_logger

    return get_task_logger(__name__)


if config.DEBUG:
    # Use redis in dev so that people don't need to setup AWS credentials.
    redis_port = os.getenv("REDIS_PORT", "6379")
    broker_url = f"redis://redis:{redis_port}/0"
    transport_options = {}
else:
    broker_url = "sqs://{}:{}@".format(
        safequote(config.AWS_ACCESS_KEY_ID), safequote(config.AWS_SECRET_ACCESS_KEY)
    )
    transport_options = {"region": "us-west-1", "visibility_timeout": 120}


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

if config.TESTING:
    celery.conf.update(task_always_eager=True, task_eager_propagates=True)


class ContextTask(celery.Task):  # type: ignore
    def __call__(self, *args, **kwargs):
        # If an "app_context" has already been loaded, just pass through
        if flask._app_ctx_stack.top is not None:
            return super().__call__(*args, **kwargs)
        with config.app.app_context():
            return self.run(*args, **kwargs)

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        get_celery_logger().exception(
            "%s: %s", type(exc).__name__, str(exc), exc_info=exc
        )
        super().on_failure(exc, task_id, args, kwargs, einfo)


celery.Task = ContextTask


@signals.setup_logging.connect
def setup_celery_logging(**kwargs):
    dictConfig(config.LOGGING_CONFIG)


celery.autodiscover_tasks(["airq"])
