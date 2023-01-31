from __future__ import annotations

import logging
from .const import DOMAIN

_LOGGER: logging.Logger = logging.getLogger(__package__)
_LOGGER = logging.getLogger(__name__)


DOMAIN = "viggo"

# RAW API CODE BELOW
from bs4 import BeautifulSoup as BS
from datetime import date, datetime, timedelta, time
import requests
import os
import re
import gc

DEBUG = False

INPUT_FINGERPRINT = "fingerprint"
INPUT_PASSWORD = "Password"
INPUT_USERNAME = "UserName"
INPUT_RETURN_URL = "returnUrl"

AJAX = "&ajax=1"
PAGESIZE = "&pagesize=100000"
VIEW = "&view=List"
HOME = "&home=true"
USER_ID = "&userId="
BBS = "BBS"
BBS_DETAILS = "BBS_DETAILS"
LOGOUT = "LOGOUT"
MSG_DETAILS = "MSG_DETAILS"
MSG_FOLDER = "MSG_FOLDER"
MSG_FOLDERS = "MSG_FOLDERS"
RELATIONS = "RELATIONS"
SCHEDULE = "SCHEDULE"

MONTHS = [
    "jan",
    "feb",
    "mar",
    "apr",
    "maj",
    "jun",
    "jul",
    "aug",
    "sep",
    "okt",
    "nov",
    "dec",
]
URLS = {}


class viggo_api:
    session = requests.Session()
    schoolName, logoUrl = None, None
    loggedIn = False
    fingerPrint = None
    unreadMsg = -1
    unreadBbs = -1
    userFullName = None
    userImg = None
    bbs = {}
    # 	relations = []
    relations = {}

    def __init__(self, url="", username="", password=""):
        self.baseUrl = url
        self.username = username
        self.password = password
        self.msgBox = mailbox()
        if not DEBUG:
            self.fingerPrintFile = (
                "./config/custom_components/"
                + DOMAIN
                + "/fingerprints/"
                + self.username
            )
        else:
            self.fingerPrintFile = self.username

    def update(self):
        self._login()

        self._fetchRelations()
        self._fetchSchedule()

        self._fetchFolders()
        self._fetchMsg()

        self._fetchBbs()

        collected = gc.collect()
        print(f"Garbage collector: collected {collected} objects.")

    def getMsgFolders(self):
        return self.msgBox.folders.values()

    def getBbs(self):
        return self.bbs.values()

    def _login(self, soup=None):
        # Have we been here before - did we bring soup...?
        if soup is None:
            soup = self._fetchHtml(self.baseUrl)
        if soup:
            self.loggedIn = (
                soup.select_one("form[action='/Basic/Account/Login']") is None
            )
            if not self.loggedIn:
                # Prepare a payload for login
                payload = {
                    INPUT_USERNAME: self.username,
                    INPUT_PASSWORD: self.password,
                    INPUT_RETURN_URL: soup.select_one(
                        f"input[name={INPUT_RETURN_URL}]"
                    )["value"],
                }

                # Is there a saved fingerprint from a previous session, then load
                # Else extract it from the login form and save it to file
                if os.path.isfile(self.fingerPrintFile):
                    with open(self.fingerPrintFile, "r") as f:
                        payload[INPUT_FINGERPRINT] = f.read()
                else:
                    with open(self.fingerPrintFile, "w") as f:
                        payload[INPUT_FINGERPRINT] = soup.select_one(
                            "input[name='fingerprint']"
                        )["value"]
                        f.write(payload[INPUT_FINGERPRINT])
                self.fingerPrint = payload[INPUT_FINGERPRINT]

                # Send the payload
                soup = self._fetchHtml(
                    url=self.baseUrl + soup.find("form")["action"], postData=payload
                )
                if soup:
                    # First login since last session
                    if not LOGOUT in URLS:
                        URLS[LOGOUT] = soup.select_one("li[class='logout']").a["href"]
                        # Name and Logo of school
                        infoTag = soup.select_one("div[id='client-name']")
                        self.schoolName = infoTag.div.text
                        self.logoUrl = infoTag.img["src"]
                    self._login(soup)
            else:
                # We are logged in - lets get to work....
                msgTag = soup.select_one("div[id='notification-messages']").a
                bbsTag = soup.select_one("div[id='notification-user']").a
                imgTag = soup.select_one("ul[id='nav-user']").img

                # Messages
                self.unreadMsg = int(msgTag["data-amount"])
                URLS[MSG_FOLDERS] = msgTag["href"]

                # Bulletins
                self.unreadBbs = int(bbsTag["data-amount"])
                # NEEDS IMPROVEMENT
                URLS[BBS] = (
                    re.search(".*\('(.*),", bbsTag["onclick"])
                    .group(1)
                    .split(",")[0]
                    .replace("'", "")
                )

                # Userinfo
                self.userImg = imgTag["src"]
                self.userFullName = imgTag.parent.span.text

                # Extract the URL to the page with relations
                URLS[RELATIONS] = soup.select_one(
                    "section[data-confidential='relations']"
                )["data-load-url"]

            # Clean up
            soup.decompose()

    def _fetchRelations(self):
        soup = self._fetchHtml(self.baseUrl + URLS[RELATIONS])

        # Extract relations
        for relations in soup.find("ul").find_all("li"):
            id = relations["data-relation-id"]
            self.relations[str(id)] = relation(
                id, relations.a.text, relations.img["src"]
            )

            # There are a 2nd <li> ignore
            break

        # Extract URL for the schedule
        url_payload = re.search(
            "viggo.ajax.loadHtml\(`(.*)\?(.*)`", soup.find("script").text
        )
        URLS[SCHEDULE] = url_payload.group(1) + "?" + HOME + VIEW + AJAX + USER_ID

    def _fetchSchedule(self):
        # For every relation
        for id in self.relations.keys():
            # Fetch the schedule
            soup = self._fetchHtml(self.baseUrl + URLS[SCHEDULE] + id)
            if soup:
                # Find every event
                events = soup.find_all("li", class_="")
                for eventTags in events:
                    dates = []
                    for dateList in eventTags.find(
                        "div", class_="hint event"
                    ).div.text.split(" - "):
                        dateList = dateList.replace(".", "").strip(" ").split(" ")
                        d = str(dateList[0]).zfill(2)
                        m = str(MONTHS.index(dateList[1]) + 1).zfill(2)
                        y = datetime.today().year if len(dateList) < 4 else dateList[2]
                        t = dateList[-1]
                        dates.append(
                            datetime.strptime(f"{d}-{m}-{y} {t}", "%d-%m-%Y %H:%M")
                        )
                    self.relations[id].addEvent(
                        event(
                            dates,
                            eventTags.strong.text,
                            eventTags.find("small", class_="p").text.strip("( )"),
                        )
                    )

    def _fetchFolders(self, url=None):
        # If first run, fecth the "pretty" but useless page with folders
        firstRun = not url
        if firstRun:
            url = URLS[MSG_FOLDERS]

        soup = self._fetchHtml(self.baseUrl + url + "?" + AJAX)
        if soup:
            # If this is still the first run, extract the correct link for page with the folders
            # Call the function again.
            if firstRun:
                urlTag = re.search(
                    "(.*){id=([0-9]*)}",
                    soup.select_one("ul[id='folderRoot']")["data-load-url"],
                )
                self._fetchFolders(url=urlTag.group(1))
            else:
                # Find all foldernames and their urls
                # Ignore drafts folder (id = -1)
                for url in soup.find_all("a"):
                    folderTag = re.search("(.*/)([0-9]*)", url["href"])
                    if folderTag.group(2):
                        # If this is the first run extrac the URL for a folder
                        if not MSG_FOLDER in URLS:
                            URLS[MSG_FOLDER] = folderTag.group(1)
                        self.msgBox.addFolder(
                            mailFolder(url.text.strip(), folderTag.group(2))
                        )

            # Clean up
            soup.decompose()

    def _fetchMsg(self):
        for folder in self.msgBox.folders.values():
            soup = self._fetchHtml(
                self.baseUrl + URLS[MSG_FOLDER] + folder.id + "?" + AJAX + PAGESIZE
            )
            if soup:
                msgList = soup.find_all("li", class_="contextmenu")
                for msg in msgList:
                    # If this is the first run, extra url for a message details
                    if not MSG_DETAILS in URLS:
                        URLS[MSG_DETAILS] = re.search(
                            f"(.*/){folder.id}",
                            msg.find("a", href=re.compile("#message-details"))["href"],
                        ).group(1)
                    id = msg.find("input", {"name": "MessageId"})["value"]
                    senderImg = msg.a.img["src"]
                    senderName = msg.a.small.previous_sibling.string
                    date = self._dateFromStr(msg.a.small.string)
                    subject = msg.a.find("div", class_="h").string
                    preview = msg.a.find_all("div")[-1].string
                    self.msgBox.addMsgToFolder(
                        folder.id,
                        message(id, senderImg, senderName, date, subject, preview),
                    )
                # Clean up
                soup.decompose()

    def _fetchBbs(self):
        soup = self._fetchHtml(self.baseUrl + URLS[BBS])
        if soup:
            for bulletinTag in soup.find_all("a", href=re.compile("Bulletin#modal")):
                bbsName = bulletinTag.strong.string
                if not bbsName in self.bbs:
                    self.bbs[bbsName] = bulletinBoard(bbsName)
                idTag = re.search("(.*/)([0-9]*)?.*", bulletinTag["href"])
                if not BBS_DETAILS in URLS:
                    URLS[BBS_DETAILS] = idTag.group(1)
                soup = self._fetchHtml(
                    self.baseUrl + URLS[BBS_DETAILS] + idTag.group(2)
                )
                if soup.li:
                    senderImg = soup.li.img["src"]
                    senderName = soup.li.a.small.previous_sibling.string
                    date = self._dateFromStr(soup.li.a.small.string)
                    contentTag = soup.li.find("div")
                    subject = contentTag.strong.string
                    self.bbs[bbsName].addBulletin(
                        bulletin(idTag.group(2), senderImg, senderName, date, subject)
                    )

            # Clean up
            soup.decompose()

    def _fetchHtml(self, url=None, parser="html.parser", postData=None, timeout=5):
        if url is None:
            return False

        if postData == None:
            r = self.session.get(url, timeout=5)
        else:
            r = self.session.post(url, data=postData, timeout=5)
        if r.status_code == 200:
            return BS(r.text, parser)
        return r.status_code

    def _dateFromStr(self, dateStr: str):
        dateList = dateStr.split(" ")
        #        if "få" in dateStr:
        #            return datetime.now()
        if "sekund" in dateStr:
            return datetime.now() - timedelta(seconds=int(dateList[0]))
        if "minut" in dateStr:
            return datetime.now() - timedelta(minutes=int(dateList[0]))
        if "time" in dateStr:
            return datetime.now() - timedelta(hours=int(dateList[0]))
        if "går" in dateStr:
            return datetime.strptime(
                str(date.today()) + " " + dateList[-1], "%Y-%m-%d %H:%M"
            ) - timedelta(days=1)
        d = str(dateList[0][:-1]).zfill(2)
        m = str(MONTHS.index(dateList[1]) + 1).zfill(2)
        y = datetime.today().year if len(dateList) < 4 else dateList[2]
        t = dateList[-1]
        return datetime.strptime(f"{d}-{m}-{y} {t}", "%d-%m-%Y %H:%M")


class relation:
    id, name, image = None, None, None
    schedule = []

    def __init__(self, id, name, image):
        self.id = id
        self.name = name
        self.image = image

    def addEvent(self, event: object):
        self.schedule.append(event)


class event:
    dateStart, dateEnd, title, location = None, None, None, None

    def __init__(self, dates, title, location):
        self.dateStart = dates[0]
        self.dateEnd = dates[1]
        self.title = title
        self.location = location


class mailbox:
    folders = {}
    inbox, sent, draft = None, None, None

    def __init__(self):
        pass

    def addFolder(self, folderObj: object):
        self.folders[folderObj.id] = folderObj
        folderName = folderObj.name.lower()
        if "indbakke" in folderName:
            self.inbox = self.folders[folderObj.id]
            return
        if "kladder" in folderName:
            self.draft = self.folders[folderObj.id]
            return
        if "sendt" in folderName:
            self.sent = self.folders[folderObj.id]
            return

    def addMsgToFolder(self, folderId: str, msg: object):
        if self.folders and folderId in self.folders.keys():
            self.folders[folderId].addMsg(msg)


class mailFolder:
    id = 0
    size = 0

    def __init__(self, folderName: str, id):
        self.id = str(id)
        self.name = folderName
        self.messages = {}

    def addMsg(self, msg: object):
        self.messages[msg.id] = msg
        self.size = len(self.messages)

    def getMessages(self):
        return self.messages.values()

    def getFirstMessage(self):
        return self.messages[list(self.messages.keys())[0]]


class message:
    def __init__(
        self,
        id: int,
        senderImg: str,
        senderName: str,
        date: datetime,
        subject: str,
        preview: str,
    ):
        self.id = id
        self.senderImg = senderImg
        self.senderName = senderName
        self.date = date
        self.subject = subject
        self.preview = preview


class bulletinBoard:
    size = 0

    def __init__(self, name: str) -> None:
        self.name = name
        self.bulletins = {}

    def addBulletin(self, bulletin):
        self.bulletins[bulletin.id] = bulletin
        self.size = len(self.bulletins)

    def getBulletins(self):
        return self.bulletins.values()

    def getFirstBulletin(self):
        return self.bulletins[list(self.bulletins.keys())[0]]


class bulletin:
    def __init__(
        self, id: str, senderImg: str, senderName: str, date: datetime, subject: str
    ) -> None:
        self.id = id
        self.senderImg = senderImg
        self.senderName = senderName
        self.date = date
        self.subject = subject
