from airq import config  # Do this first, it initializes everything
from airq.celery import celery  # This is necesary to start celery

from airq import api
from airq import commands


app = config.app

# Register commands
app.cli.command("sync")(commands.sync)

# Register routes
app.route("/", methods=["GET"])(api.healthcheck)
app.route("/sms", methods=["POST"])(api.sms_reply)
app.route("/quality", methods=["GET"])(api.quality)
