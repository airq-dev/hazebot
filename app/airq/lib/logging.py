import logging
import traceback

from flask import request

from airq import config
from airq.lib import ses


class AdminEmailHandler(logging.Handler):
    def emit(self, record: logging.LogRecord):
        if not record.exc_info:
            return
        _, exc, _ = record.exc_info
        subject = "[{}]: {}".format(type(exc).__name__, str(exc)[:100])
        body = "{}\n\n{}".format(str(exc), traceback.format_exc())
        if request:
            body += "\n"
            for key, value in request.environ.items():
                body += "{}={}\n".format(key, value)
        ses.send_email(config.ADMIN_EMAILS, subject, body)
