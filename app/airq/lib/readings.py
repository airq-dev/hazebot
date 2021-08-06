import dataclasses
import enum
import math
import typing

from flask_babel import gettext

from airq.lib.choices import IntChoicesEnum
from airq.lib.choices import StrChoicesEnum


@enum.unique
class ConversionFactor(StrChoicesEnum):
    """Determines how we will adjust the determine pm25."""

    NONE = "None"
    US_EPA = "US EPA"

    @property
    def display(self) -> str:
        if self == self.US_EPA:
            return gettext("US EPA")
        else:
            return gettext("None")

    def convert(self, readings: "Readings") -> float:
        """Convert raw data into a pm25 we can use."""
        if (
            self == self.US_EPA
            and readings.pm_cf_1 is not None
            and readings.humidity is not None
        ):
            return _us_epa_conv(readings.pm_cf_1, readings.humidity)
        else:
            return readings.pm25


@enum.unique
class Pm25(IntChoicesEnum):
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


@dataclasses.dataclass
class Readings:
    """Encapsulates a set of readings from PurpleAir."""

    pm25: float
    pm_cf_1: typing.Optional[float]
    humidity: typing.Optional[float]

    def get_pm25(self, conversion_factor: ConversionFactor) -> float:
        """Get the pm25 according to the given conversion strategy."""
        return conversion_factor.convert(self)

    def get_pm25_level(self, conversion_factor: ConversionFactor) -> Pm25:
        """Get the pm25 level according to the given conversion strategy."""
        return Pm25.from_measurement(self.get_pm25(conversion_factor))

    def get_aqi(self, conversion_stragy: ConversionFactor) -> int:
        """Get the aqi according to the given conversion strategy."""
        return _pm25_to_aqi(self.get_pm25(conversion_stragy))


def _pm25_to_aqi(concentration: float) -> int:
    if 350.5 < concentration:
        return _linear(500, 401, 500, 350.5, concentration)
    elif 250.5 < concentration:
        return _linear(400, 301, 350.4, 250.5, concentration)
    elif 150.5 < concentration:
        return _linear(300, 201, 250.4, 150.5, concentration)
    elif 55.5 < concentration:
        return _linear(200, 151, 150.4, 55.5, concentration)
    elif 35.5 < concentration:
        return _linear(150, 101, 55.4, 35.5, concentration)
    elif 12.1 < concentration:
        return _linear(100, 51, 35.4, 12.1, concentration)
    else:
        return _linear(50, 0, 12, 0, concentration)


def _linear(
    aqi_high: int, aqi_low: int, conc_high: float, conc_low: float, concentration: float
) -> int:
    return math.ceil(
        ((concentration - conc_low) / (conc_high - conc_low)) * (aqi_high - aqi_low)
        + aqi_low
    )


def _us_epa_conv(pm_cf_1: float, humidity: float) -> float:
    # See https://cfpub.epa.gov/si/si_public_record_report.cfm?dirEntryId=349513&Lab=CEMM
    return (0.534 * pm_cf_1) - (0.0844 * humidity) + 5.604
