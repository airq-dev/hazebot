import traceback

from airq import config
from airq.lib import ses


def handle_exc(exc: Exception):
    subject = "[{}]: {}".format(type(exc).__name__, str(exc)[:100])
    body = "{}\n\n{}".format(str(exc), traceback.format_exc())
    ses.send_email(config.ADMIN_EMAILS, subject, body)
