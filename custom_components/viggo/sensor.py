"""Platform for sensor integration."""
from __future__ import annotations

import logging

from datetime import timedelta

from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import CONF_CLIENT, CONF_PLATFORM, DOMAIN, UPDATE_INTERVAL, CREDITS

from homeassistant.const import ATTR_ATTRIBUTION, ATTR_ENTITY_PICTURE

ATTR_BULLETINS = "bulletins"
ATTR_MESSAGES = "messages"
ATTR_SCHOOL_LOGO = "school_logo_url"
ATTR_USER_IMAGE = "user_image"

_LOGGER: logging.Logger = logging.getLogger(__package__)
_LOGGER = logging.getLogger(__name__)


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):

    # Define a update function
    async def async_update_data():
        # Retrieve the client stored in the hass data stack
        viggo = hass.data[DOMAIN][CONF_CLIENT]
        # Call, and wait for it to finish, the function with the refresh procedure
        await hass.async_add_executor_job(viggo.update)

    # Create a coordinator
    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=CONF_PLATFORM,
        update_method=async_update_data,
        update_interval=timedelta(minutes=UPDATE_INTERVAL),
    )

    # Immediate refresh
    await coordinator.async_request_refresh()

    # Add sensors to Home Assistant
    viggo = hass.data[DOMAIN][CONF_CLIENT]
    sensors = [
        ViggoUserSensor(coordinator, viggo),
        ViggoUnreadSensor(coordinator, viggo, viggo.unreadMsg, " Nye beskeder"),
        ViggoUnreadSensor(coordinator, viggo, viggo.unreadBbs, " Nye opslag"),
    ]
    for folder in viggo.getMsgFolders():
        sensors.append(
            ViggoMsgFolderSensor(
                coordinator,
                viggo,
                folder,
                5,
                5,
            )
        )
    for bbs in viggo.getBbs():
        sensors.append(ViggoBbsSensor(coordinator, viggo, bbs, 2))
    async_add_entities(sensors)


class ViggoUserSensor(SensorEntity):
    def __init__(self, coordinator, viggo) -> None:
        self.coordinator = coordinator
        self.viggo = viggo

    @property
    def name(self):
        return self.viggo.schoolName

    @property
    def icon(self):
        return "mdi:school"

    @property
    def state(self):
        return self.viggo.userFullName

    @property
    def unique_id(self):
        return self.name + self.viggo.fingerPrint

    @property
    def extra_state_attributes(self):
        # Calculate the sunrise and sunset from the coordinates of the HA server
        attr = {
            ATTR_ENTITY_PICTURE: self.viggo.logoUrl,
            ATTR_USER_IMAGE: self.viggo.userImg,
            ATTR_ATTRIBUTION: CREDITS,
        }
        return attr

    @property
    def should_poll(self):
        """No need to poll. Coordinator notifies entity of updates."""
        return False

    @property
    def available(self):
        """Return if entity is available."""
        return self.coordinator.last_update_success

    async def async_update(self):
        """Update the entity. Only used by the generic entity update service."""
        await self.coordinator.async_request_refresh()

    async def async_added_to_hass(self):
        """When entity is added to hass."""
        self.async_on_remove(
            self.coordinator.async_add_listener(self.async_write_ha_state)
        )


class ViggoUnreadSensor(SensorEntity):
    def __init__(self, coordinator, viggo, unread, namePostfix) -> None:
        self.coordinator = coordinator
        self.viggo = viggo
        self.unread = unread
        self.namePostfix = namePostfix

    @property
    def name(self):
        return self.viggo.schoolName + self.namePostfix

    @property
    def icon(self):
        return "mdi:email-alert"

    @property
    def state(self):
        return self.unread

    @property
    def unique_id(self):
        return self.name + self.viggo.fingerPrint

    @property
    def extra_state_attributes(self):
        return {ATTR_ATTRIBUTION: CREDITS}

    @property
    def should_poll(self):
        """No need to poll. Coordinator notifies entity of updates."""
        return False

    @property
    def available(self):
        """Return if entity is available."""
        return self.coordinator.last_update_success

    async def async_update(self):
        """Update the entity. Only used by the generic entity update service."""
        await self.coordinator.async_request_refresh()

    async def async_added_to_hass(self):
        """When entity is added to hass."""
        self.async_on_remove(
            self.coordinator.async_add_listener(self.async_write_ha_state)
        )


class ViggoMsgFolderSensor(SensorEntity):
    def __init__(self, coordinator, viggo, folder, showMsg=0, detailLevel=1) -> None:
        self.coordinator = coordinator
        self.viggo = viggo
        self.folder = folder
        self.showMsg = showMsg
        self.detailLevel = detailLevel

    @property
    def name(self):
        return self.viggo.schoolName + " " + self.folder.name

    @property
    def icon(self):
        return "mdi:inbox"

    @property
    def state(self):
        return self.folder.size

    @property
    def unique_id(self):
        return self.name + self.viggo.fingerPrint

    @property
    def extra_state_attributes(self):
        attr = {}
        if self.showMsg > 0 and self.folder.size > 0:
            attr[ATTR_MESSAGES] = []
            i = 0
            for msgObj in self.folder.getMessages():
                if i >= self.showMsg:
                    break
                msg = {}
                if self.detailLevel >= 1:
                    msg.update({"from": msgObj.senderName, "subject": msgObj.subject})
                if self.detailLevel >= 2:
                    msg.update({"date": msgObj.date})
                if self.detailLevel >= 3:
                    msg.update({"preview": msgObj.preview})
                if self.detailLevel >= 4:
                    msg.update({"image": msgObj.senderImg})
                # if self.detailLevel >= 5:
                #     msg.pop("preview")
                #     msg.update({"message": msgObj.content})
                attr[ATTR_MESSAGES].append(msg)
                i += 1

        attr[ATTR_ATTRIBUTION] = CREDITS
        return attr

    @property
    def should_poll(self):
        """No need to poll. Coordinator notifies entity of updates."""
        return False

    @property
    def available(self):
        """Return if entity is available."""
        return self.coordinator.last_update_success

    async def async_update(self):
        """Update the entity. Only used by the generic entity update service."""
        await self.coordinator.async_request_refresh()

    async def async_added_to_hass(self):
        """When entity is added to hass."""
        self.async_on_remove(
            self.coordinator.async_add_listener(self.async_write_ha_state)
        )


class ViggoBbsSensor(SensorEntity):
    def __init__(self, coordinator, viggo, bbs, showMsg=0, detailLevel=1) -> None:
        self.coordinator = coordinator
        self.viggo = viggo
        self.bbs = bbs
        self.showMsg = showMsg
        self.detailLevel = detailLevel

    @property
    def name(self):
        return self.viggo.schoolName + " " + self.bbs.name

    @property
    def icon(self):
        return "mdi:bulletin-board"

    @property
    def state(self):
        return self.bbs.size

    @property
    def unique_id(self):
        return self.name + self.viggo.fingerPrint

    @property
    def extra_state_attributes(self):
        attr = {}
        if self.showMsg > 0 and self.bbs.size > 0:
            attr[ATTR_BULLETINS] = []
            i = 0
            for bbsObj in self.bbs.getBulletins():
                if i >= self.showMsg:
                    break
                bbs = {}
                if self.detailLevel >= 1:
                    bbs.update({"from": bbsObj.senderName, "subject": bbsObj.subject})
                if self.detailLevel >= 2:
                    bbs.update({"date": bbsObj.date})
                if self.detailLevel >= 3:
                    bbs.update({"preview": bbsObj.content})
                if self.detailLevel >= 4:
                    bbs.update({"image": bbsObj.senderImg})
                attr[ATTR_BULLETINS].append(bbs)
                i += 1

        attr[ATTR_ATTRIBUTION] = CREDITS
        return attr

    @property
    def should_poll(self):
        """No need to poll. Coordinator notifies entity of updates."""
        return False

    @property
    def available(self):
        """Return if entity is available."""
        return self.coordinator.last_update_success

    async def async_update(self):
        """Update the entity. Only used by the generic entity update service."""
        await self.coordinator.async_request_refresh()

    async def async_added_to_hass(self):
        """When entity is added to hass."""
        self.async_on_remove(
            self.coordinator.async_add_listener(self.async_write_ha_state)
        )
