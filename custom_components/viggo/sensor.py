"""Platform for sensor integration."""
from __future__ import annotations

import logging

from datetime import timedelta

from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import (
    CONF_CLIENT,
    CONF_CONFIG,
    CONF_PLATFORM,
    CONF_UPDATE_INTERVAL,
    DOMAIN,
    CREDITS,
)


from homeassistant.const import ATTR_ATTRIBUTION, ATTR_ENTITY_PICTURE

ATTR_BULLETINS = "bulletins"
ATTR_MESSAGES = "messages"
ATTR_SCHEDULE = "schedule"
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

    # Retrieve Viggo and config
    viggo = hass.data[DOMAIN][CONF_CLIENT]
    conf = hass.data[DOMAIN][CONF_CONFIG]
    UPDATE_INTERVAL = conf[CONF_UPDATE_INTERVAL]

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
    sensors = []
    if conf["userinfo"]:
        sensors.append(ViggoUserSensor(coordinator, viggo))
    if conf["unread"]:
        sensors.append(ViggoUnreadSensor(coordinator, viggo, "msg", " Nye beskeder"))
        sensors.append(ViggoUnreadSensor(coordinator, viggo, "bbs", " Nye opslag"))
    conf["amount"] = 1000 if conf["amount"] < 0 else conf["amount"]
    if conf["amount"] > 0:
        for folder in viggo.getMsgFolders():
            sensors.append(
                ViggoMsgFolderSensor(
                    coordinator,
                    viggo,
                    folder,
                    conf["amount"],
                    conf["details"],
                )
            )
        for bbs in viggo.getBbs():
            sensors.append(
                ViggoBbsSensor(
                    coordinator,
                    viggo,
                    bbs,
                    conf["amount"],
                    conf["details"],
                )
            )
    if conf["relations"]:
        for relation in viggo.relations.values():
            sensors.append(
                ViggoRelationSensor(
                    coordinator,
                    relation,
                    viggo.schoolName,
                    viggo.fingerPrint,
                    conf["schedule"],
                )
            )
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


class ViggoRelationSensor(SensorEntity):
    def __init__(
        self, coordinator, relation, schoolName, fingerPrint, showSchedule
    ) -> None:
        self.coordinator = coordinator
        self.relation = relation
        self.schoolName = schoolName
        self.fingerPrint = fingerPrint
        self.showSchedule = showSchedule

    @property
    def name(self):
        return self.schoolName + " " + self.relation.name

    @property
    def icon(self):
        return "mdi:account-school"

    @property
    def state(self):
        if self.relation.schedule:
            return self.relation.schedule[0].title
        return ""

    @property
    def unique_id(self):
        return self.relation.name + self.fingerPrint

    @property
    def extra_state_attributes(self):
        # Calculate the sunrise and sunset from the coordinates of the HA server
        attr = {
            ATTR_ENTITY_PICTURE: self.relation.image,
            ATTR_ATTRIBUTION: CREDITS,
        }
        if self.showSchedule:
            attr[ATTR_SCHEDULE] = []
            for event in self.relation.schedule:
                attr[ATTR_SCHEDULE].append(
                    {
                        "date_start": event.dateStart,
                        "date_end": event.dateEnd,
                        "title": event.title,
                        "location": event.location,
                    }
                )

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
    def __init__(self, coordinator, viggo, type, namePostfix) -> None:
        self.coordinator = coordinator
        self.viggo = viggo
        self.type = type
        self.namePostfix = namePostfix

    @property
    def name(self):
        return self.viggo.schoolName + self.namePostfix

    @property
    def icon(self):
        if self.type == "msg":
            return "mdi:email-alert"
        else:
            return "mdi:bell"

    @property
    def state(self):
        if self.type == "msg":
            return self.viggo.unreadMsg
        else:
            return self.viggo.unreadBbs

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
    def __init__(self, coordinator, viggo, folder, showMsg, details) -> None:
        self.coordinator = coordinator
        self.viggo = viggo
        self.folder = folder
        self.showMsg = showMsg
        self.details = details

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

        if self.folder.size > 0:
            msgObj = self.folder.getFirstMessage()
            if "sender_name" in self.details:
                attr["from"] = msgObj.senderName
            if "date" in self.details:
                attr["date"] = msgObj.date
            if "subject" in self.details:
                attr["subject"] = msgObj.subject
            if "preview" in self.details:
                attr["preview"] = msgObj.preview
            if "sender_image" in self.details:
                attr[ATTR_ENTITY_PICTURE] = msgObj.senderImg

            attr[ATTR_MESSAGES] = []
            i = 0
            for msgObj in self.folder.getMessages():
                if i >= self.showMsg:
                    break
                msg = {}
                if "sender_name" in self.details:
                    msg.update({"from": msgObj.senderName})
                if "date" in self.details:
                    msg.update({"date": msgObj.date})
                if "subject" in self.details:
                    msg.update({"subject": msgObj.subject})
                if "preview" in self.details:
                    msg.update({"preview": msgObj.preview})
                if "sender_image" in self.details:
                    msg.update({"image": msgObj.senderImg})
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
    def __init__(self, coordinator, viggo, bbs, showMsg, details) -> None:
        self.coordinator = coordinator
        self.viggo = viggo
        self.bbs = bbs
        self.showMsg = showMsg
        self.details = details

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

        if self.bbs.size > 0:
            bbsObj = self.bbs.getFirstBulletin()
            if "sender_name" in self.details:
                attr["from"] = bbsObj.senderName
            if "date" in self.details:
                attr["date"] = bbsObj.date
            if "subject" in self.details:
                attr["subject"] = bbsObj.subject
            #        if "preview" in self.details:
            #            attr["content"] = bbsObj.content
            if "sender_image" in self.details:
                attr[ATTR_ENTITY_PICTURE] = bbsObj.senderImg

            attr[ATTR_BULLETINS] = []
            i = 0
            for bbsObj in self.bbs.getBulletins():
                if i >= self.showMsg:
                    break
                bbs = {}
                if "sender_name" in self.details:
                    bbs.update({"from": bbsObj.senderName})
                if "date" in self.details:
                    bbs.update({"date": bbsObj.date})
                if "subject" in self.details:
                    bbs.update({"subject": bbsObj.subject})
                # if "preview" in self.details:
                #     bbs.update({"content": bbsObj.content})
                if "sender_image" in self.details:
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
