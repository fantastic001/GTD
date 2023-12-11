from dataclasses import asdict, field, fields
import datetime
from typing import Any
from urllib.parse import non_hierarchical

import jira
import json 
import os

from jira.resources import Issue 

config = json.loads(open(os.environ.get("GTD_CONFIG", os.path.join(os.environ["HOME"],".config", "gtd.json"))).read())

ctrl = jira.JIRA(config["url"], basic_auth=(config["username"], config["password"]))



def ticket(ticket: Issue, extended = False) -> str:
    return "[<a href='%s'>%s</a>] %s (%s)%s%s" % (
        "https://fantastic001.atlassian.net/browse/%s" % ticket.key,
        ticket.key, 
        ticket.fields.summary, 
        ticket.fields.status,
        "(Due %s)" % ticket.fields.duedate if extended and ticket.fields.duedate is not None else "",
        ": %s" % ", ".join(
            [c.body for c in ticket.fields.comment.comments]
        ) if extended and len(ticket.fields.comment.comments) > 0 else ""
    )

def colored(c, text):
    return "<span style=\"background-color: %s\">%s</span>" % (c, text)


def blue(text):
    return colored("aqua", text)


def green(text):
    return colored("lime", text)

def yellow(text):
    return colored("yellow", text)


def red(text):
    return colored("red", text)

def img(src):
    return "<img src='%s' />" % src 

def items(l: list[Any]):
    return "<ul>\n%s</ul>" % "\n".join("<li>%s</li>" % str(t) for t in l)

def tickets(l, extended=False):
    return items([ticket(t, extended=extended) for t in l])

def section(text, level=0):
    return "<h%d>%s</h%d>" % (level+1, text, level+1)

def paragraph(text):
    return "<p>%s</p>" % text 

class CommandExecutor:
    def search(self, jql: str): 
        return ctrl.search_issues(jql, maxResults=None) 
    
    def get_free_slots(self, *, flatten: bool = False, only_once: bool = False):
        tickets: list[jira.Issue] = self.search("issuetype = Task AND statuscategory != Done AND duedate < 60days AND duedate is not empty")
        duedates = [ticket.fields.duedate for ticket in tickets]
        result = [] 
        for t in [datetime.date.today() + datetime.timedelta(days=i) for i in range(60)]:
            formatted = t.strftime(r"%Y-%m-%d")
            amount = len([d for d in duedates if d == formatted])
            result.append((formatted, amount))
        result =  [(x,(4-y) if not only_once else 1) for x,y in result if y < 4]
        if flatten:
            return [[r[0]] * r[1] for r in result]
        else:
            return result
        
    def retro(self, * ,use_html: bool = False):
        tasks: list[Issue] = self.search("filter = 'weekly retro'")
        epics = [task.raw.get("fields", {}).get("parent", {}).get("fields", {}).get("summary", "") for task in tasks]
        NON_PROJECT_EPIC_SUMMARY = "Non-project related tasks"
        epics.append(NON_PROJECT_EPIC_SUMMARY)
        epics = set(epics)
        result = [] 
        epic_to_tasks = {}
        for epic in epics:
            if epic == "":
                epic = NON_PROJECT_EPIC_SUMMARY
            epic_to_tasks[epic] = [] 
        for task in tasks:
            epic_summary = task.raw.get("fields", {}).get("parent", {}).get("fields", {}).get("summary", "")
            if epic_summary == "":
                epic_summary = NON_PROJECT_EPIC_SUMMARY
            epic_to_tasks[epic_summary].append(task)
        for epic, tasks_in_epic in epic_to_tasks.items():
            if epic == "":
                epic = NON_PROJECT_EPIC_SUMMARY
            if len(tasks_in_epic) == 0:
                continue
            if use_html:
                result.append(section(epic, level=1))
            else:
                result.append("* %s" % epic)
                result.append("")
            if use_html:
                result.append(tickets(tasks_in_epic, extended=True))
            else:
                for task in tasks_in_epic:
                    result.append("+ %s " % task.fields.summary)
                result.append("")
        if use_html:
            result.append(section("Statistics", level=1))
            result.append(paragraph("Number of Finished tasks: %d" % len(tasks)))
            result.append(paragraph("Number of Finished tasks without project: %d" % len(epic_to_tasks[NON_PROJECT_EPIC_SUMMARY])))
        else:
            result.append("* Statistics")
            result.append("")
            result.append("+ Number of Finished tasks: %d" % len(tasks))
            result.append("+ Number of Finished tasks without project: %d" % len(epic_to_tasks[NON_PROJECT_EPIC_SUMMARY]))        
        return result

    def report(self):
        bad_tickets = self.search("filter = 'Badly specified tasks'")
        bad_epics = self.search("filter = 'Badly specified epics'")
        tickets_overdue = self.search("filter = 'Tasks this week' and duedate < endOFDay()")
        tickets_this_week = self.search("filter = 'Tasks this week'")
        contexts = [task.raw["fields"]["customfield_10036"]["value"] for task in tickets_this_week]
        context_tasks = {
            c: [t for t in tickets_this_week if t.raw["fields"]["customfield_10036"]["value"] == c] for c in contexts
        }
        result = [] 
        rating = ""
        if len(bad_tickets) > 0 or len(bad_epics) > 0 or len(tickets_overdue) > 1:
            rating = red("Bad")
        elif len(tickets_overdue) > 0 or len(tickets_this_week) > 21:
            rating = yellow("Concerning")
        elif len(tickets_this_week) > 5:
            rating = green("Good")
        else:
            rating = blue("Excellent")
        result.append(paragraph("Overall rating: %s" % rating))
        result.append(section("Due this week"))
        for context, tasks in context_tasks.items():
            result.append(section(context, 1))
            result.append(tickets(tasks))
        result.append(section("Delegated tasks"))
        result.append(tickets(self.search("filter = 'Delegated'"), extended=True))
        result.append(section("Non-urgent tasks focus of the day"))
        if len(tickets_overdue) == 0 and len(tickets_this_week) < 21:
            result.append(tickets(self.search("filter = 'Backlog' and duedate is empty")[:10]))
        else:
            result.append(tickets(self.search("filter = 'Backlog' and duedate is empty")[:1]))
        result.append(section("Weekly retro"))
        result += self.retro(use_html=True)
        result.append(section("Badly specified tickets"))
        if len(bad_tickets) > 0:
            result.append(tickets(bad_tickets))
        else:
            result.append(paragraph("There are no badly specified tickets"))
        result.append(section("Badly specified epics"))
        if len(bad_epics) > 0:
            result.append(tickets(bad_epics))
        else:
            result.append(paragraph("There are no badly specified epics"))
        result.append(section("Report of available days"))
        result.append(paragraph("The following days are available to be used as due dates:"))
        result.append(items(self.get_free_slots(flatten=True, only_once=True)))

        return result 
        
    def get_critical_days(self, *, days: int = 32):
        tickets = self.search("issuetype = Task AND statuscategory != Done AND duedate < %ddays" % days)
        result = {}
        d = {} 
        for t in tickets:
            d[t.fields.duedate] = d.get(t.fields.duedate, []) + [t]
        for day, tasks in d.items():
            if len(tasks) > 4:
                result[day] = [x.fields.summary for x in tasks] 
        return result