# coding: utf-8

import pywikibot
import mwparserfromhell as mwparser
import jinja2

import re
import codecs
import datetime


class UnblockRequestError(Exception):
    def __init__(self, desc):
        self.desc = desc


class UnblockRequest:
    def __init__(self, site, page: pywikibot.Page):
        self.site = site
        self.page = page
        self.user = None
        self.is_ipuser = False
        self.is_blocked = False
        self.is_range_blocked = False
        self.sysop = None
        self.timestamp_blocked = None
        self.reason_blocked = None
        self.timestamp_submitted = None
        self.revid_submitted = None
        self.iprange = None
        self.expiry = None

        # identify the user who requested unblock
        self.identify_user()

        # identify the revision at which unblock was requested
        self.identify_submitted_revision()

        # get the log created with the block
        self.get_log()

    def identify_user(self):
        namespace = self.page.namespace()
        if namespace == 3:
            self.user = self.page.title().split(":")[1]
        if re.match(r"[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+", self.user):
            self.is_ipuser = True

    def identify_submitted_revision(self):
        user = None
        for revision in self.page.fullVersionHistory():
            wikitext = mwparser.parse(revision.text)
            templates = wikitext.filter_templates()
            for template in templates:
                if template.name in ("Unblock", "unblock"):
                    submitter = revision.user
                    timestamp_submitted = revision.timestamp
                    revid_submitted = revision.revid
                    break
            else:
                break
        self.timestamp_submitted = timestamp_submitted
        self.revid_submitted = revid_submitted

    def get_log(self):
        if self.is_ipuser:
            for log in self.site.blocks(iprange=self.user):
                self.sysop = log["by"]
                self.reason_blocked = log["reason"]
                self.timestamp_blocked = log["timestamp"]
                self.is_blocked = True
                self.iprange = log["user"]
                self.expiry = log["expiry"]
                break
        else:
            for log in self.site.blocks(users=self.user):
                self.sysop = log["by"]
                self.reason_blocked = log["reason"]
                self.timestamp_blocked = log["timestamp"]
                self.expiry = log["expiry"]
                self.is_blocked = True
                break


def gen_unblock_requests(site):
    cat = pywikibot.Category(site, "Category:ブロック解除依頼")
    for page in cat.members():
        if page.is_categorypage():
            continue
        yield page


class LogPage:
    def __init__(self, kwargs: dict, page_name="User:Akasenbot/UnblockRequests"):
        self.page_name = page_name
        self.rendered = None
        self.kwargs = kwargs

    def render(self):
        env = jinja2.Environment(loader=jinja2.FileSystemLoader("./", encoding="utf-8"))
        template = env.get_template("logpage.tmp")
        self.kwargs.update({"today":datetime.datetime.today().isoformat(), "pagename":self.page_name})
        self.rendered = template.render(self.kwargs)

    def save(self):
        with codecs.open("temp.txt", "w", "utf-8") as f:
            f.write(self.rendered)


if __name__ == "__main__":
    jawp = pywikibot.Site()
    requests = list()
    range_blocks = list()
    errors = list()
    for request in gen_unblock_requests(jawp):
        req = UnblockRequest(jawp, request)
        if req.is_blocked:
            if req.iprange:
                range_blocks.append(req)
            else:
                requests.append(req)
        else:
            errors.append(req)
    for request in requests:
        print(vars(request))
    logpage = LogPage({"requests":requests, "range_blocks":range_blocks, "errors":errors})
    logpage.render()
    logpage.save()

