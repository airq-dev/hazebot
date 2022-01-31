import os
import typing
from logging.config import dictConfig

if typing.TYPE_CHECKING:
    from airq.models.users import User


FLASK_ENV = os.getenv("FLASK_ENV", "development")
DEV = FLASK_ENV == "development"
TESTING = FLASK_ENV == "test"
PROD = FLASK_ENV == "production"
DEBUG = not PROD

SECRET_KEY = os.getenv(
    "SECRET_KEY", "c3ab8ff13720e8ad9047dd39466b3c8974e592c2fa383d4a3960714caef0c4f2"
)

AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID", "")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "")

ADMIN_EMAILS = os.getenv("ADMIN_EMAILS", "").split(",")

SES_REGION = os.getenv("SES_REGION", "us-west-2")
SES_EMAIL_SOURCE = os.getenv("SES_EMAIL_SOURCE", "info@hazebot.org")

TWILIO_AUTHTOKEN = os.getenv("TWILIO_AUTHTOKEN", "")
TWILIO_NUMBERS = {
    "en": os.getenv("TWILIO_NUMBER_EN", ""),
    "es": os.getenv("TWILIO_NUMBER_ES", ""),
}
TWILIO_SID = os.getenv("TWILIO_SID", "")

PURPLEAIR_API_KEY = os.getenv("PURPLEAIR_API_KEY", "")

PG_DB = os.getenv("POSTGRES_DB", "postgres")
PG_HOST = os.getenv("POSTGRES_HOST", "db")
PG_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")
PG_PORT = os.getenv("POSTGRES_POST", "5432")
PG_USER = os.getenv("POSTGRES_USER", "postgres")

SERVER_URL = os.getenv("SERVER_URL", "localhost:80")


# Init logging before doing anything else.
#
# TODO: Send errors to admins as emails
LOGGING_CONFIG: typing.Dict[str, typing.Any] = {
    "version": 1,
    "disable_existing_loggers": True,
    "formatters": {
        "default": {
            "format": "[%(asctime)s] %(levelname)s in %(module)s: %(message)s",
        }
    },
    "handlers": {
        "wsgi": {
            "class": "logging.StreamHandler",
            "stream": "ext://flask.logging.wsgi_errors_stream",
            "formatter": "default",
        },
        "mail_admins": {
            "class": "airq.lib.logging.AdminEmailHandler",
            "formatter": "default",
            "level": "ERROR",
        },
    },
    "root": {
        "level": "ERROR" if TESTING else "INFO",
        "handlers": ["wsgi", "mail_admins"],
    },
}
dictConfig(LOGGING_CONFIG)

import flask
import flask_login
import flask_migrate
import flask_sqlalchemy
import flask_wtf
from flask import g
from flask import got_request_exception
from flask_babel import Babel
from airq import middleware

app = flask.Flask(__name__)
app.secret_key = SECRET_KEY

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
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
config = {
    "HAZEBOT_ENABLED": bool(int(os.getenv("HAZEBOT_ENABLED", 1))),
    "HAZEBOT_SHARE_REQUESTS_ENABLED": os.getenv("HAZEBOT_SHARE_REQUESTS_ENABLED", True),
    "BABEL_DEFAULT_LOCALE": "en",
    "BABEL_TRANSLATION_DIRECTORIES": os.path.join(base_dir, "translations"),
    "SQLALCHEMY_DATABASE_URI": f"postgresql+psycopg2://{PG_USER}:{PG_PASSWORD}@{PG_HOST}:{PG_PORT}/{PG_DB}",
    "SQLALCHEMY_TRACK_MODIFICATIONS": False,
}
app.config.from_mapping(config)
babel = Babel(app)
db = flask_sqlalchemy.SQLAlchemy(app)
migrate = flask_migrate.Migrate(app, db)
login = flask_login.LoginManager(app)

csrf = flask_wtf.csrf.CSRFProtect()
csrf.init_app(app)


@babel.localeselector
def get_locale():
    return g.locale


@login.user_loader
def load_user(user_id: str) -> typing.Optional["User"]:
    from airq.models.users import User

    user = User.query.get(int(user_id))
    if user:
        g.user = user
    return user


def log_exception(sender, exception, **extra):
    app.logger.exception(exception)


got_request_exception.connect(log_exception, app)
