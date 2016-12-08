# -*- coding: utf-8 -*-
# @author: zoidberg

from __future__ import unicode_literals
from __future__ import division

from past.utils import old_div
import re
from time import mktime, strptime
from pyload.plugins.account import Account
from pyload.plugins.internal.simplehoster import parseHtmlForm
from pyload.utils import parseFileSize


class XFSPAccount(Account):
    __name__ = "XFSPAccount"
    __version__ = "0.05"
    __type__ = "account"
    __description__ = """XFileSharingPro base account plugin"""
    __author_name__ = "zoidberg"
    __author_mail__ = "zoidberg@mujmail.cz"

    MAIN_PAGE = None

    VALID_UNTIL_PATTERN = r'>Premium.[Aa]ccount expire:</TD><TD><b>([^<]+)</b>'
    TRAFFIC_LEFT_PATTERN = r'>Traffic available today:</TD><TD><b>([^<]+)</b>'

    def loadAccountInfo(self, user, req):
        html = req.load(self.MAIN_PAGE + "?op=my_account", decode=True)

        validuntil = trafficleft = None
        premium = True if '>Renew premium<' in html else False

        found = re.search(self.VALID_UNTIL_PATTERN, html)
        if found:
            premium = True
            trafficleft = -1
            try:
                self.logDebug(found.group(1))
                validuntil = mktime(strptime(found.group(1), "%d %B %Y"))
            except Exception as e:
                self.logError(e)
        else:
            found = re.search(self.TRAFFIC_LEFT_PATTERN, html)
            if found:
                trafficleft = found.group(1)
                if "Unlimited" in trafficleft:
                    premium = True
                else:
                    trafficleft = old_div(parseFileSize(trafficleft), 1024)

        return ({"validuntil": validuntil, "trafficleft": trafficleft, "premium": premium})

    def login(self, user, data, req):
        html = req.load('%slogin.html' % self.MAIN_PAGE, decode=True)

        action, inputs = parseHtmlForm('name="FL"', html)
        if not inputs:
            inputs = {"op": "login",
                      "redirect": self.MAIN_PAGE}

        inputs.update({"login": user,
                       "password": data['password']})

        html = req.load(self.MAIN_PAGE, post=inputs, decode=True)

        if 'Incorrect Login or Password' in html or '>Error<' in html:
            self.wrongPassword()
