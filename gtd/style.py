
from jira import Issue
import pandas as pd 
from typing import Any


def ticket(ticket: Issue, extended = False) -> str:
    if not isinstance(ticket, dict):
        return "[<a href='%s'>%s</a>] %s (%s)%s%s" % (
            ("https://fantastic001.atlassian.net/browse/%s" % ticket.key),
            ticket.key,
            ticket.fields.summary,
            ticket.fields.status,
            "(Due %s)" % ticket.fields.duedate if extended and ticket.fields.duedate is not None else "",
            ": %s" % ", ".join(
                [c.body for c in ticket.fields.comment.comments]
            ) if extended and len(ticket.fields.comment.comments) > 0 else ""
        )
    else:
        return "[<a href='%s'>%s</a>] %s" % (
            ticket["shortUrl"],
            ticket["shortLink"],
            ticket["name"],
        )

def colored(c, text, block=False):
    if not block:
        return "<span style=\"background-color: %s\">%s</span>" % (c, text)
    else:
        return "<div style=\"background-color: %s\">%s</div>" % (c, text)


def blue(text, block=False):
    return colored("aqua", text, block)


def green(text, block=False):
    return colored("lime", text, block)

def yellow(text, block=False):
    return colored("yellow", text, block)


def red(text, block=False):
    return colored("red", text, block)

def img(src):
    return "<img src='%s' />" % src 

def items(l: list[Any]):
    return "<ul>\n%s</ul>" % "\n".join("<li>%s</li>" % str(t) for t in l)


def section(text, level=0):
    return "<h%d>%s</h%d>" % (level+1, text, level+1)

def paragraph(text):
    return "<p>%s</p>" % text 

def table(table_records):
    return pd.DataFrame(table_records).to_html(index=False, escape=False)
