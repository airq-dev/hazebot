from airq import config  # Do this first, it initializes everything
from airq.celery import celery  # This is necesary to start celery

from airq.controllers import admin
from airq.controllers import api
from airq import management


app = config.app

# Register management commands
app.cli.command("generate-fixtures")(management.generate_fixtures)
app.cli.command("sync")(management.sync)

# Register routes
# TODO: Change '/' to be the admin page,
# and repoint healthcheck /healthcheck
app.route("/", methods=["GET"])(api.healthcheck)
app.route("/healthcheck", methods=["GET"])(api.healthcheck)
app.route("/test/<string:locale>", methods=["GET"])(api.test_command)
app.route("/sms/<string:locale>", methods=["POST"])(api.sms_reply)

# Admin routes
app.route("/login", methods=["GET", "POST"])(admin.login)
app.route("/logout", methods=["GET"])(admin.logout)
app.route("/admin", methods=["GET"])(admin.admin_summary)
app.route("/admin/bulk-sms", methods=["GET", "POST"])(admin.admin_bulk_sms)
app.route("/admin/bulk-upload", methods=["GET", "POST"])(admin.upload_users)
app.route("/admin/sms", methods=["GET", "POST"])(admin.admin_sms)
app.route("/admin/stats", methods=["GET"])(admin.admin_stats)
