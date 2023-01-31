from __future__ import annotations

import logging

from .viggo_api import viggo_api
from .const import (
    CONF_CLIENT,
    CONF_CONFIG,
    CONF_DEFAULT,
    CONF_SHOW,
    CONF_PLATFORM,
    CONF_PASSWORD,
    CONF_UPDATE_INTERVAL,
    CONF_URL,
    CONF_USERNAME,
    DOMAIN,
    UPDATE_INTERVAL,
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

    # Loop the custom config
    # If the config key exist in the default config, update it
    for confKey, confValue in conf.get(CONF_SHOW, {}).items():
        if confKey in CONF_DEFAULT.keys():
            CONF_DEFAULT.update({confKey: confValue})
    CONF_DEFAULT[CONF_UPDATE_INTERVAL] = conf.get(CONF_UPDATE_INTERVAL, UPDATE_INTERVAL)

    # Add Viggo and the config to the stack
    hass.data[DOMAIN] = {CONF_CLIENT: viggo, CONF_CONFIG: CONF_DEFAULT}

    # Add sensors
    hass.async_create_task(
        hass.helpers.discovery.async_load_platform(CONF_PLATFORM, DOMAIN, conf, config)
    )

    # Initialization was successful.
    return True
