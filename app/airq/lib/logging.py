import logging
import traceback

from flask import request

from airq import config


def get_airq_logger(name: str) -> logging.Logger:
    return logging.getLogger("airq." + name)


class AdminEmailHandler(logging.Handler):
    def emit(self, record: logging.LogRecord):
        from airq.lib import ses

        if record.exc_info:
            _, exc, _ = record.exc_info
        else:
            exc = None

        if exc:
            exc_title = type(exc).__name__
        else:
            exc_title = "Error"

        subject = f"{exc_title} at {record.pathname}:{record.lineno}"

        body = record.getMessage()
        if exc:
            if body:
                body += "\n"
            body += "ERROR:\n"
            body += str(exc) + "\n"
            body += "TRACEBACK:\n"
            body += traceback.format_exc()

        if request:
            body += "\n"
            for key, value in request.environ.items():
                body += "{}={}\n".format(key, value)

        ses.send_email(config.ADMIN_EMAILS, subject, body)
