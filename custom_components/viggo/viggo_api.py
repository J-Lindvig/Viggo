from __future__ import annotations

import logging

_LOGGER: logging.Logger = logging.getLogger(__package__)
_LOGGER = logging.getLogger(__name__)

# RAW API CODE BELOW
from bs4 import BeautifulSoup as BS
from datetime import datetime, timedelta
import requests
import os
import re

INPUT_FINGERPRINT = "fingerprint"
INPUT_PASSWORD = "Password"
INPUT_USERNAME = "UserName"
INPUT_RETURN_URL = "returnUrl"

AJAX = "?ajax=1"
BBS = "BBS"
BBS_DETAILS = "BBS_DETAILS"
LOGOUT = "LOGOUT"
MSG_DETAILS = "MSG_DETAILS"
MSG_FOLDER = "MSG_FOLDER"
MSG_FOLDERS = "MSG_FOLDERS"

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
    soup, schoolName, logoUrl = None, None, None
    loggedIn = False
    fingerPrint = None
    unreadMsg = -1
    unreadBbs = -1
    userFullName = None
    userImg = None
    bbs = {}

    def __init__(self, url="", username="", password=""):
        self.baseUrl = url
        self.username = username
        self.password = password
        self.msgBox = mailbox()

    def update(self):
        self._login()

        self._fetchFolders()
        self._fetchMsg()
        # This accidently "reads" the messages....
        # self._fetcgMsgContent()

        self._fetchBbs()

    def getMsgFolders(self):
        return self.msgBox.folders.values()

    def getBbs(self):
        return self.bbs.values()

    def _login(self, soup=None):
        # Have we been here before - did we bring soup...?
        if soup is None:
            _LOGGER.debug("Login, first run...")
            soup = self._fetchHtml(self.baseUrl)
        if soup:
            self.loggedIn = (
                soup.select_one("form[action='/Basic/Account/Login']") is None
            )
            _LOGGER.debug(f"Logged in: {self.loggedIn}")
            if not self.loggedIn:
                # Prepare a payload for login
                payload = {
                    INPUT_USERNAME: self.username,
                    INPUT_PASSWORD: self.password,
                    INPUT_RETURN_URL: soup.select_one(
                        f"input[name={INPUT_RETURN_URL}]"
                    )["value"],
                }

                # Is there a saved finngerprint from a previous session, then load
                # Else extract it from the login form and save it to file
                if os.path.isfile(self.username):
                    with open(self.username, "r") as f:
                        payload[INPUT_FINGERPRINT] = f.read()
                else:
                    with open(self.username, "w") as f:
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

    def _fetchFolders(self, url=None):
        # If first run, fecth the "pretty" but useless page with folders
        firstRun = not url
        if firstRun:
            url = URLS[MSG_FOLDERS]

        soup = self._fetchHtml(self.baseUrl + url + AJAX)
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
                for url in soup.find_all("a"):
                    folderTag = re.search("(.*/)(-?[0-9]*)", url["href"])
                    # If this is the first run extrac the URL for a folder
                    if not MSG_FOLDER in URLS:
                        URLS[MSG_FOLDER] = folderTag.group(1)
                    self.msgBox.addFolder(
                        mailFolder(url.text.strip(), folderTag.group(2))
                    )

    def _fetchMsg(self):
        for folder in self.msgBox.folders.values():
            soup = self._fetchHtml(self.baseUrl + URLS[MSG_FOLDER] + folder.id + AJAX)
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

    # def _fetcgMsgContent(self):
    #     for folder in self.msgBox.folders.values():
    #         for msg in folder.messages.values():
    #             soup = self._fetchHtml(
    #                 self.baseUrl + URLS[MSG_DETAILS] + folder.id + "/" + msg.id + AJAX
    #             )
    #             if soup:
    #                 msg.content = soup.find("div", class_="p").contents

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
                    content = contentTag.find("div", class_="content").contents
                    self.bbs[bbsName].addBulletin(
                        bulletin(
                            idTag.group(2),
                            senderImg,
                            senderName,
                            date,
                            subject,
                            content,
                        )
                    )

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

    def _dateFromStr(self, date: str):
        dateList = date.split(" ")
        if "få" in date:
            return datetime.now()
        if "sekund" in date:
            return datetime.now() - timedelta(seconds=int(dateList[0]))
        elif "minut" in date:
            return datetime.now() - timedelta(minutes=int(dateList[0]))
        elif "time" in date:
            return datetime.now() - timedelta(hours=int(dateList[0]))
        else:
            d = str(dateList[0][:-1]).zfill(2)
            m = str(MONTHS.index(dateList[1]) + 1).zfill(2)
            y = datetime.today().year if len(dateList) < 4 else dateList[2]
            t = dateList[-1]
            return datetime.strptime(f"{d}-{m}-{y} {t}", "%d-%m-%Y %H:%M")


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


class bulletin:
    def __init__(
        self,
        id: str,
        senderImg: str,
        senderName: str,
        date: datetime,
        subject: str,
        content: str,
    ) -> None:
        self.id = id
        self.senderImg = senderImg
        self.senderName = senderName
        self.date = date
        self.subject = subject
        self.content = content
