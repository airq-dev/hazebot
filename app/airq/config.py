import os
import logging
import typing
from logging.config import dictConfig


FLASK_ENV = os.getenv("FLASK_ENV", "development")
DEBUG = FLASK_ENV == "development"

AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID", "")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "")

ADMIN_EMAILS = os.getenv("ADMIN_EMAILS", "").split(",")

SES_REGION = os.getenv("SES_REGION", "")
SES_EMAIL_SOURCE = os.getenv("SES_EMAIL_SOURCE", "")

TWILIO_AUTHTOKEN = os.getenv("TWILIO_AUTHTOKEN", "")
TWILIO_NUMBER = os.getenv("TWILIO_NUMBER", "")
TWILIO_SID = os.getenv("TWILIO_SID", "")

PG_DB = os.getenv("POSTGRES_DB", "postgres")
PG_HOST = os.getenv("POSTGRES_HOST", "db")
PG_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")
PG_PORT = os.getenv("POSTGRES_POST", "5432")
PG_USER = os.getenv("POSTGRES_USER", "postgres")


# Init logging before doing anything else.
#
# TODO: Send errors to admins as emails
LOGGING_CONFIG: typing.Dict[str, typing.Any] = {
    "version": 1,
    "disable_existing_loggers": True,
    "formatters": {
        "default": {"format": "[%(asctime)s] %(levelname)s in %(module)s: %(message)s",}
    },
    "handlers": {
        "wsgi": {
            "class": "logging.StreamHandler",
            "stream": "ext://flask.logging.wsgi_errors_stream",
            "formatter": "default",
        }
    },
    "root": {"level": "INFO", "handlers": ["wsgi"]},
}
if not DEBUG:
    LOGGING_CONFIG["handlers"]["mail_admins"] = {
        "class": "airq.lib.logging.AdminEmailHandler",
        "formatter": "default",
        "level": "ERROR",
    }
    LOGGING_CONFIG["root"]["handlers"].append("mail_admins")
dictConfig(LOGGING_CONFIG)

import flask
import flask_migrate
import flask_sqlalchemy
from flask import got_request_exception
from airq import middleware

app = flask.Flask(__name__)

# We have to use this `setattr` hack here or Mypy gets really confused.
# See https://github.com/python/mypy/issues/2427 for details.
setattr(app, "wsgi_app", middleware.LoggingMiddleware(app.wsgi_app))
setattr(
    app,
    "wsgi_app",
    middleware.ProfilerMiddleware(
        app.wsgi_app, restrictions=[30], sort_by=("cumtime", "tottime")
    ),
)

config = {
    "SQLALCHEMY_DATABASE_URI": f"postgresql+psycopg2://{PG_USER}:{PG_PASSWORD}@{PG_HOST}:{PG_PORT}/{PG_DB}",
    "SQLALCHEMY_TRACK_MODIFICATIONS": False,
}
app.config.from_mapping(config)

db = flask_sqlalchemy.SQLAlchemy(app)
migrate = flask_migrate.Migrate(app, db)


def log_exception(sender, exception, **extra):
    app.logger.exception(exception)


got_request_exception.connect(log_exception, app)
