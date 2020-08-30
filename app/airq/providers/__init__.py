import enum

from airq.providers import airnow
from airq.providers import purpleair


class ProviderType(str, enum.Enum):
    AIRNOW = "airnow"
    PURPLEAIR = "purpleair"


def get_message_for_zipcode(zipcode, provider_type=None):
    if not provider_type:
        provider_type = ProviderType.AIRNOW

    if provider_type == ProviderType.AIRNOW:
        return airnow.get_message_for_zipcode(zipcode)
    elif provider_type == ProviderType.PURPLEAIR:
        return purpleair.get_message_for_zipcode(zipcode)
