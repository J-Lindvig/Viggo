from __future__ import annotations

import logging
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

from .viggo_api import viggo_api
from .const import (
    CONF_CLIENT,
    DOMAIN,
    CONF_PLATFORM,
    CONF_PASSWORD,
    CONF_URL,
    CONF_USERNAME,
)

_LOGGER: logging.Logger = logging.getLogger(__package__)
_LOGGER = logging.getLogger(__name__)


async def async_setup(hass, config):
    # Get the configuration
    conf = config.get(DOMAIN)
    # If no config, abort
    if conf is None:
        return True

    # Create a instance of Viggo
    viggo = viggo_api(
        url=conf.get(CONF_URL, ""),
        username=conf.get(CONF_USERNAME, ""),
        password=conf.get(CONF_PASSWORD, ""),
    )

    hass.data[DOMAIN] = {CONF_CLIENT: viggo}

    # Add sensors
    hass.async_create_task(
        hass.helpers.discovery.async_load_platform(CONF_PLATFORM, DOMAIN, conf, config)
    )

    # Initialization was successful.
    return True
