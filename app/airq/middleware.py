import json
import logging
import time


logger = logging.getLogger(__name__)


class LoggingMiddleware:
    KEYS = {
        "HTTP_USER_AGENT",
        "REQUEST_METHOD",
        "REQUEST_URI",
    }

    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        info = {}
        for key in self.KEYS:
            value = environ.get(key)
            if value:
                info[key] = value

        start_ts = time.perf_counter()

        def _start_response(status, headers, exc_info=None):
            info["DURATION"] = time.perf_counter() - start_ts
            info["RESPONSE_CODE"] = status
            logger.info("api_info: %s", json.dumps(info))
            return start_response(status, headers, exc_info)

        return self.app(environ, _start_response)
