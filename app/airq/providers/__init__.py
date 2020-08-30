import typing

from airq.providers.base import Provider, ProviderType
from airq.providers.airnow import AirnowProvider
from airq.providers.purpleair import PurpleairProvider


PROVIDERS = [AirnowProvider(), PurpleairProvider()]


def get_providers(provider_types: typing.List[str]) -> typing.List[Provider]:
    # Coerce to list of provider types
    provider_types = list(filter(bool, provider_types))

    if not provider_types:
        return PROVIDERS
    else:
        providers = []
        for provider_type in provider_types:
            for provider in PROVIDERS:
                if provider.TYPE == provider_type:
                    providers.append(provider)

        if providers:
            return providers

    return []
