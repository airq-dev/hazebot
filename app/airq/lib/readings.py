import enum
import math
import typing

from flask_babel import gettext


@enum.unique
class Pm25(enum.IntEnum):
    GOOD = 0
    MODERATE = 12
    UNHEALTHY_FOR_SENSITIVE_GROUPS = 35
    UNHEALTHY = 55
    VERY_UNHEALTHY = 150
    HAZARDOUS = 250

    @classmethod
    def from_measurement(cls, measurement: float) -> "Pm25":
        if measurement < cls.MODERATE:
            return cls.GOOD
        if measurement < cls.UNHEALTHY_FOR_SENSITIVE_GROUPS:
            return cls.MODERATE
        if measurement < cls.UNHEALTHY:
            return cls.UNHEALTHY_FOR_SENSITIVE_GROUPS
        if measurement < cls.VERY_UNHEALTHY:
            return cls.UNHEALTHY
        if measurement < cls.HAZARDOUS:
            return cls.VERY_UNHEALTHY

        return cls.HAZARDOUS

    @property
    def display(self) -> str:
        if self == self.GOOD:
            return gettext("GOOD")
        elif self == self.MODERATE:
            return gettext("MODERATE")
        elif self == self.UNHEALTHY_FOR_SENSITIVE_GROUPS:
            return gettext("UNHEALTHY FOR SENSITIVE GROUPS")
        elif self == self.UNHEALTHY:
            return gettext("UNHEALTHY")
        elif self == self.VERY_UNHEALTHY:
            return gettext("VERY UNHEALTHY")
        else:
            return gettext("HAZARDOUS")

    @property
    def description(self) -> str:
        if self == self.GOOD:
            return gettext(
                "GOOD (AQI: 0 - 50) means air quality is considered satisfactory, and air pollution poses little or no risk."
            )
        elif self == self.MODERATE:
            return gettext(
                "MODERATE (AQI: 51 - 100) means air quality is acceptable; however, for some pollutants there may be a moderate health concern for a very small number of people who are unusually sensitive to air pollution."
            )
        elif self == self.UNHEALTHY_FOR_SENSITIVE_GROUPS:
            return gettext(
                "UNHEALTHY FOR SENSITIVE GROUPS (AQI: 101 - 150) means members of sensitive groups may experience health effects. The general public is not likely to be affected."
            )
        elif self == self.UNHEALTHY:
            return gettext(
                "UNHEALTHY (AQI: 151 - 200) means everyone may begin to experience health effects; members of sensitive groups may experience more serious health effects."
            )
        elif self == self.VERY_UNHEALTHY:
            return gettext(
                "VERY UNHEALTHY (AQI: 201 - 300): Health alert. Everyone may experience more serious health effects."
            )
        else:
            return gettext(
                "HAZARDOUS (AQI: 301 - 500): Health warnings of emergency conditions. The entire population is more likely to be affected."
            )


def pm25_to_aqi(concentration: float) -> typing.Optional[int]:
    c = math.floor(10 * concentration) / 10
    if c >= 0 and c < 12.1:
        return _linear(50, 0, 12.0, 0.0, c)
    if c >= 12.1 and c < 35.5:
        return _linear(100, 51, 35.4, 12.1, c)
    if c >= 35.5 and c < 55.5:
        return _linear(150, 101, 55.4, 35.5, c)
    if c >= 55.5 and c < 150.5:
        return _linear(200, 151, 150.4, 55.5, c)
    if c >= 150.5 and c < 250.5:
        return _linear(300, 201, 250.4, 150.5, c)
    if c >= 250.5 and c < 350.5:
        return _linear(400, 301, 350.4, 250.5, c)
    if c >= 350.5 and c < 500.5:
        return _linear(500, 401, 500.4, 350.5, c)

    return None


def _linear(
    aqi_high: int, aqi_low: int, conc_high: float, conc_low: float, concentration: float
) -> int:
    return round(
        ((concentration - conc_low) / (conc_high - conc_low)) * (aqi_high - aqi_low)
        + aqi_low
    )
