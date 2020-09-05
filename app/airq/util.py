import enum
import math


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
            return cls.VERY_UNHEALTHY
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
