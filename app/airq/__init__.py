from airq import config  # Do this first, it initializes everything
from airq.celery import celery  # This is necesary to start celery

from airq import api
from airq import management


app = config.app

# Register management commands
app.cli.command("sync")(management.sync)

# Register routes
app.route("/", methods=["GET"])(api.healthcheck)
app.route("/login", methods=["GET", "POST"])(api.login)
app.route("/test", methods=["GET"])(api.test_command)
app.route("/sms", methods=["POST"])(api.sms_reply)
