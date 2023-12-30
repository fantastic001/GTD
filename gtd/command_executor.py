from dataclasses import asdict, field, fields
import datetime
from typing import Any
from urllib.parse import non_hierarchical
import pandas as pd 
import jira
import json 
import os
import requests 


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

def tickets(l, extended=False):
    if all([x.fields.duedate is not None for x in l]):
        l = sorted(l, key= lambda x: datetime.datetime.strptime(x.fields.duedate, "%Y-%m-%d"))
    return items([ticket(t, extended=extended) for t in l])

def section(text, level=0):
    return "<h%d>%s</h%d>" % (level+1, text, level+1)

def paragraph(text):
    return "<p>%s</p>" % text 

def table(table_records):
    return pd.DataFrame(table_records).to_html(index=False, escape=False)
class CommandExecutor:
    def search(self, jql: str, expand: bool = False): 
        return ctrl.search_issues(jql, maxResults=None, expand=expand) 
    
    def graphql_call(self, query, **vars):
        response = requests.post(
            url=config["url"]+"/rest/graphql/1/", 
            auth=(config["username"], config["password"]), 
            json={
                'query': query,
                "variables": vars
            })
        return response
    
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
        result = [] 
        # Rating 
        bad_tickets = self.search("filter = 'Badly specified tasks'")
        bad_epics = self.search("filter = 'Badly specified epics'")
        tickets_overdue = self.search("filter = 'Tasks this week' and duedate < endOFDay()")
        tickets_this_week = self.search("filter = 'Tasks this week'")
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
        
        # average resolution rate in past week 
        resolved = self.search("resolved > -7days")
        rate = len(resolved) / 7
        if rate >= 4 and rate < 6:
            rate = green("%.2f" % rate)
        elif rate < 4:
            rate = yellow("%.2f" % rate)
        else:
            rate = blue("%.2f" % rate)
        result.append(paragraph("Resolution rate: " + rate))

        # Due this week 
        contexts = [task.raw["fields"]["customfield_10036"]["value"] for task in tickets_this_week]
        context_tasks = {
            c: [t for t in tickets_this_week if t.raw["fields"]["customfield_10036"]["value"] == c] for c in contexts
        }
        result.append(section("Due this week"))
        for context, tasks in context_tasks.items():
            result.append(section(context, 1))
            result.append(tickets(tasks, extended=True))
        result.append(section("Delegated tasks"))
        result.append(tickets(self.search("filter = 'Delegated'"), extended=True))
        result.append(section("Non-urgent tasks focus of the day"))
        if len(tickets_overdue) == 0 and len(tickets_this_week) < 21:
            result.append(tickets(self.search("filter = 'Backlog' and duedate is empty")[:10]))
        else:
            result.append(tickets(self.search("filter = 'Backlog' and duedate is empty")[:1]))

        # Weekly retro
        result.append(section("Weekly retro"))
        result += self.retro(use_html=True)
        
        
        # Badly specificed 
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
        
        # Report of available days
        result.append(section("Report of available days"))
        result.append(paragraph("The following days are available to be used as due dates:"))
        result.append(items(self.get_free_slots(flatten=True, only_once=True)))
        
        # Critical days 
        critical_days = self.get_critical_days()
        if len(critical_days.keys()) > 0:
            result.append(section("Days with many tasks due"))
            for day, tasks in critical_days:
                result.append(section(day, level=1))
                result.append(items(tasks))

        # Context distribution 
        result.append(section("Context distribution"))
        result.append(table(self.get_context_distribution()))
        return result 
    
    def get_context_distribution(self):
        tasks = self.search("filter = 'Tasks this month'")
        fields = self.graphql_call("""
            query fieldConfigurationQuery($issueKey: String) { 
                issue(issueIdOrKey: $issueKey, latestVersion: true, screen: \"view\") {
                          fields {
                                key
                                schema {
                                    type
                                    custom
                                    customId
                                    system
                                    renderer
                                }
                                autoCompleteUrl
                                allowedValues\n        
                                operations        
                                required
                                editable
                                title
                            }    
                        }
            }
        """,
        issueKey=tasks[0].key
        ).json()["data"]["issue"]["fields"]
        context_field = [f for f in fields if f["title"] == "Context"][0]

        contexts = [c["value"] for c in context_field["allowedValues"]]
        context_tasks = {
            c: [t for t in tasks if t.raw["fields"]["customfield_10036"]["value"] == c] for c in contexts
        }
        return [
            {
                "Context": c,
                "Number of tickets": len(t),
                "%": self.show_context_share(c, (100*len(t) / len(tasks)))
            } for c,t in context_tasks.items()
        ]

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
    
    def show_context_share(self, c, percentage):
        rules = {
            "Work": {
                "max": 40,
                "min": 10
            },
            "Petnica": {
                "max": 20,
                "min": 0
            },
            "University": {
                "min": 20,
                "max": 100
            }
        }
        limits = rules.get(c, {
            "max": 100,
            "min": 0
        })
        if limits["min"] <= percentage and percentage <= limits["max"]:
            return green("%.2f%%" % percentage, block=True) 
        else:
            if percentage > limits["max"]:
                return yellow("%.2f" % percentage, block=True)
            else:
                return blue("%.2f" % percentage, block=True)
