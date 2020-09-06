import json
import logging
import time
import urllib

from werkzeug.middleware import profiler

#
# TODO: Figure out how to add typing to this file.
#


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


class ProfilerMiddleware(profiler.ProfilerMiddleware):
    """A version of Werkzeug's ProfilerMiddleware which only
    profiles a request when profile=1 is set in the query string;
    e.g., localhost:5000/quality?zipcode=94703&profile=1
    """

    def __call__(self, environ, start_response):
        query_string = environ.get("QUERY_STRING", "")
        args = urllib.parse.parse_qs(query_string)
        if args.get("profile"):
            # Profile the response.
            return super().__call__(environ, start_response)
        # Just do the default behavior; no profiling.
        return self._app(environ, start_response)
