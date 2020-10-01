from airq import config  # Do this first, it initializes everything
from airq.celery import celery  # This is necesary to start celery

from airq import api
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
app.route("/login", methods=["GET", "POST"])(api.login)
app.route("/logout", methods=["GET"])(api.logout)
app.route("/<string:locale>/test", methods=["GET"])(api.test_command)
app.route("/<string:locale>/sms", methods=["POST"])(api.sms_reply)

# Admin routes
app.route("/admin", methods=["GET"])(api.admin_summary)
app.route("/admin/bulk-sms", methods=["GET", "POST"])(api.admin_bulk_sms)
app.route("/admin/bulk-upload", methods=["GET", "POST"])(api.upload_users)
app.route("/admin/sms", methods=["GET", "POST"])(api.admin_sms)
app.route("/admin/stats", methods=["GET"])(api.admin_stats)
