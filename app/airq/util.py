import enum
import gc
import itertools
import math
import typing


@enum.unique
class PM25(enum.IntEnum):
    GOOD = 0
    MODERATE = 12
    UNHEALTHY_FOR_SENSITIVE_INDIVIDUALS = 35
    UNHEALTHY = 55
    VERY_UNHEALTHY = 150
    HAZARDOUS = 250

    @classmethod
    def from_measurement(cls, measurement: float) -> "PM25":
        if measurement < cls.MODERATE:
            return cls.GOOD
        if measurement < cls.UNHEALTHY_FOR_SENSITIVE_INDIVIDUALS:
            return cls.MODERATE
        if measurement < cls.UNHEALTHY:
            return cls.UNHEALTHY_FOR_SENSITIVE_INDIVIDUALS
        if measurement < cls.VERY_UNHEALTHY:
            return cls.UNHEALTHY
        if measurement < cls.HAZARDOUS:
            return cls.VERY_UNHEALTHY

        return cls.HAZARDOUS

    @property
    def display(self) -> str:
        if self == self.GOOD:
            return "Good"
        elif self == self.MODERATE:
            return "Moderate"
        elif self == self.UNHEALTHY_FOR_SENSITIVE_INDIVIDUALS:
            return "Unhealthy for Sensitive Individuals"
        elif self == self.UNHEALTHY:
            return "Unhealthy"
        elif self == self.VERY_UNHEALTHY:
            return "Very Unhealthy"
        else:
            return "Hazardous"


def haversine_distance(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    """
    Calculate the great circle distance between two points 
    on the earth (specified in decimal degrees)
    """
    # convert decimal degrees to radians
    lon1, lat1, lon2, lat2 = map(math.radians, [lon1, lat1, lon2, lat2])

    # haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.asin(math.sqrt(a))
    r = 6371  # Radius of earth in kilometers. Use 3956 for miles
    return c * r


def pm25_to_aqi(concentration: float) -> typing.Optional[int]:
    c = math.floor(10 * concentration) / 10
    if c >= 0 and c < 12.1:
        return linear(50, 0, 12.0, 0.0, c)
    if c >= 12.1 and c < 35.5:
        return linear(100, 51, 35.4, 12.1, c)
    if c >= 35.5 and c < 55.5:
        return linear(150, 101, 55.4, 35.5, c)
    if c >= 55.5 and c < 150.5:
        return linear(200, 151, 150.4, 55.5, c)
    if c >= 150.5 and c < 250.5:
        return linear(300, 201, 250.4, 150.5, c)
    if c >= 250.5 and c < 350.5:
        return linear(400, 301, 350.4, 250.5, c)
    if c >= 350.5 and c < 500.5:
        return linear(500, 401, 500.4, 350.5, c)

    return None


def linear(
    aqi_high: int, aqi_low: int, conc_high: float, conc_low: float, concentration: float
) -> int:
    return round(
        ((concentration - conc_low) / (conc_high - conc_low)) * (aqi_high - aqi_low)
        + aqi_low
    )


T = typing.TypeVar("T")


def chunk_list(
    iterable: typing.Iterable[T], batch_size: int = 1000
) -> typing.Iterator[typing.List[T]]:
    it = iter(iterable)
    while True:
        chunk = list(itertools.islice(it, batch_size))
        if not chunk:
            return
        yield chunk
        gc.collect()
