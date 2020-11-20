import requests
import typing

from airq.config import PURPLEAIR_API_KEY


PURPLEAIR_URL = "https://api.purpleair.com/v1/sensors"


def call_purpleair_api() -> requests.Response:
    fields = ["pm2.5", "latitude", "longitude", "last_seen", "channel_flags"]
    params: typing.Dict[str, typing.Union[int, str]] = {
        "fields": ",".join(fields),
        "location_type": 0,  # 0 is for outdoors
    }
    resp = requests.get(
        PURPLEAIR_URL,
        params=params,
        headers={"X-API-Key": PURPLEAIR_API_KEY},
    )
    resp.raise_for_status()
    return resp
