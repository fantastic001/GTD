
from gtd.extensions import load_extensions
from gtd.style import *
from gtd.config import get_config_str, get_config_bool, get_config_list
import jira 
import datetime 
import requests
import os


def get_jira_credentials():
    return (
        get_config_str("jira_username", "", "Username of jira user"),
        get_config_str("jira_password", "", "Password of jira user")
    )

def get_jira_client():
    url = get_config_str("jira_url", "", "URL of Jira instance")
    if url == "":
        return None 
    return jira.JIRA(
        url, 
        basic_auth=get_jira_credentials(),
    )


ctrl = get_jira_client()

def tickets(l, extended=False):
    if all([x.fields.duedate is not None for x in l]):
        l = sorted(l, key= lambda x: datetime.datetime.strptime(x.fields.duedate, "%Y-%m-%d"))
    return items([ticket(t, extended=extended) for t in l])

MAX_DEADLINES_PER_DAY = 1
def search(jql: str, expand: bool = False): 
    if ctrl is None:
        raise Exception("Jira client is not initialized")
    return ctrl.search_issues(jql, maxResults=None, expand=expand) 


def get_stakeholders_field(epic: jira.Issue):
    l =  epic.raw["fields"]["customfield_10038"] or []
    return [s.encode("utf-8") for s in l]
    

def get_stakeholders():
    epics = search("issuetype = Epic AND statuscategory != Done")
    
    stakeholders = []
    for i, epic in enumerate(epics):
        stakeholders += get_stakeholders_field(epic)
    stakeholders = [s.decode("utf-8") for s in stakeholders]
    stakeholder_dist = {}
    for s in stakeholders:
        stakeholder_dist[s] = stakeholder_dist.get(s, 0) + 1
    return list(sorted(stakeholder_dist.items(), key=lambda x: x[1], reverse=True))

def get_context_distribution():
    tasks = search("filter = 'Tasks this month'")
    context_field = get_context_field(tasks[0].key)
    contexts = [c["value"] for c in context_field["allowedValues"]]
    context_tasks = {
        c: [t for t in tasks if t.raw["fields"]["customfield_10036"]["value"] == c] for c in contexts
    }
    return [
        {
            "Context": c,
            "Number of tickets": len(t),
            "%": show_context_share(c, (100*len(t) / len(tasks)))
        } for c,t in context_tasks.items()
    ]

def get_critical_days(days: int = 32):
    tickets = search("issuetype = Task AND statuscategory != Done AND duedate < %ddays" % days)
    result = {}
    d = {} 
    for t in tickets:
        d[t.fields.duedate] = d.get(t.fields.duedate, []) + [t]
    for day, tasks in d.items():
        if len(tasks) > MAX_DEADLINES_PER_DAY:
            result[day] = tasks
    return result

def show_context_share(c, percentage):
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
            return yellow("%.2f%%" % percentage, block=True)
        else:
            return blue("%.2f%%" % percentage, block=True)


def graphql_call(query, **vars):
    jira_graphql_url = get_config_str("jira_graphql_url", "", "URL of Jira GraphQL endpoint")
    if jira_graphql_url == "":
        raise Exception("Jira GraphQL URL is not set")
    username, password = get_jira_credentials()
    config = {
        "url": jira_graphql_url,
        "username": username,
        "password": password
    }
    response = requests.post(
        url=config["url"]+"/rest/graphql/1/", 
        auth=(config["username"], config["password"]), 
        json={
            'query': query,
            "variables": vars
        })
    return response

def get_free_slots(flatten: bool = False, only_once: bool = False):
    tickets: list[jira.Issue] = search("issuetype = Task AND statuscategory != Done AND duedate < 60days AND duedate is not empty")
    duedates = [ticket.fields.duedate for ticket in tickets]
    result = [] 
    for t in [datetime.date.today() + datetime.timedelta(days=i) for i in range(60)]:
        formatted = t.strftime(r"%Y-%m-%d")
        amount = len([d for d in duedates if d == formatted])
        result.append((formatted, amount))
    result =  [(x,(MAX_DEADLINES_PER_DAY-y) if not only_once else 1) for x,y in result if y < MAX_DEADLINES_PER_DAY]
    if flatten:
        return [[r[0]] * r[1] for r in result]
    else:
        return result
    
def generate_report():
    result = [] 
    # Use UTF-8 encoding
    result.append("<!DOCTYPE html>")
    result.append("<html>")
    result.append("<head>")
    result.append("<meta charset='utf-8'>")
    result.append("</head>")

    result.append("<body>")
    # Rating 
    bad_tickets = search("filter = 'Badly specified tasks'")
    bad_epics = search("filter = 'Badly specified epics'")
    tickets_overdue = search("filter = 'Tasks this week' and duedate < endOFDay()")
    tickets_this_week = search("filter = 'Tasks this week'")
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
    resolved = search("resolved > -7days")
    resolved = len(resolved)
    rate = resolved / 7

    if rate >= 4 and rate < 6:
        rate = green("%.2f - keep doing 4 tasks per day!" % rate)
    elif rate < 4:
        rate = yellow("%.2f - do %d tasks today to get to rate of 4" % (rate, 32-resolved))
    else:
        rate = blue("%.2f - rest for %d days" % (rate, (resolved - 28) // 4))
    result.append(paragraph("Resolution rate: " + rate))

    # find all tasks overdue for today 
    result.append(section("Overdue tasks"))
    contexts_overdue = [task.raw["fields"]["customfield_10036"]["value"] for task in tickets_overdue]
    for context in set(contexts_overdue):
        result.append(section(context, 2))
        result.append(tickets([t for t in tickets_overdue if t.raw["fields"]["customfield_10036"]["value"] == context], extended=True))
    # Due this week 
    contexts = [task.raw["fields"]["customfield_10036"]["value"] for task in tickets_this_week]
    result.append(section("Due this week"))
    # iterate over days 
    for day in range(8):
        result.append(section((datetime.date.today() + datetime.timedelta(days=day)).strftime(r"%A, %d %B %Y"), 1))
        tasks_due_this_day = [t for t in tickets_this_week if t.fields.duedate == (datetime.date.today() + datetime.timedelta(days=day)).strftime(r"%Y-%m-%d")]
        context_tasks = {
            c: [t for t in tasks_due_this_day if t.raw["fields"]["customfield_10036"]["value"] == c] for c in contexts
        }
        for context, tasks in context_tasks.items():
            if tasks == []:
                continue
            result.append(section(context, 2))
            result.append(tickets(tasks, extended=True))
    result.append(section("Delegated tasks"))
    result.append(tickets(search("filter = 'Delegated'"), extended=True))
    result.append(section("Non-urgent tasks focus of the day"))
    if len(tickets_overdue) == 0 and len(tickets_this_week) < 21:
        result.append(tickets(search("filter = 'Backlog' and duedate is empty")[:10]))
    else:
        result.append(tickets(search("filter = 'Backlog' and duedate is empty")[:1]))

    result += load_extensions()
    
    
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
    if MAX_DEADLINES_PER_DAY == 1:
        result.append(items(get_free_slots(flatten=True, only_once=True)))
    else:
        result.append(items(get_free_slots(flatten=False, only_once=False)))
    
    # Critical days 
    critical_days = get_critical_days()
    if len(critical_days.keys()) > 0:
        result.append(section("Days with many tasks due"))
        for day, tasks in critical_days.items():
            result.append(section(day, level=1))
            result.append(tickets(tasks, extended=True))

    # Context distribution 
    if get_config_bool("show_context_distribution", False, "Show context distribution"):
        result.append(section("Context distribution"))
        if get_config_bool("show_context_distribution_table", False, "Show context distribution table"):
            result.append(table(get_context_distribution()))
        result.append(paragraph("Legend: "))
        result.append(paragraph(green("Context in expected range.")))
        result.append(paragraph(yellow("Context is hot. Decrease number of tickets.")))
        result.append(paragraph(blue("Context is cold. Increase number of tickets.")))

    result.append(section("Stakeholders"))
    sh = get_stakeholders()
    data = {
        "Name": [s[0] for s in sh],
        "Number of tickets": [s[1] for s in sh]
    }
    result.append(table(data))

    result.append(section("Other reports"))
    for report_script in get_config_list("scripts", [], "List of scripts to run for report"):
        result.append(section(report_script["name"]))
        result.append(paragraph(report_script.get("description", "")))
        result.append(paragraph("Result:"))
        escapes = {
            "\n": "<br>",
            "\t": "&nbsp;"*4,
            " ": "&nbsp;"
        }

        html_output = os.popen(report_script["script"]).read()
        if report_script.get("escape", True):
            for k,v in escapes.items():
                html_output = html_output.replace(k, v)
        result.append(paragraph(html_output))

    result.append("</body>")
    result.append("</html>")
    return result 


def get_context_field(sample_task_key: str):
    fields = graphql_call("""
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
    issueKey=sample_task_key
    ).json()["data"]["issue"]["fields"]
    context_field = [f for f in fields if f["title"] == "Context"][0]
    return context_field

def create_issue(summary: str, description: str = None, parent: str = None, context: str = None, duedate: str = None):
    """
    Create a new issue in Jira.
    :param summary: The summary of the issue.
    :param description: The description of the issue.
    :param parent: The parent issue key (if any).
    :param context: The context for the issue (if any).
    :param duedate: The due date for the issue (if any).
    :return: The created issue.
    """
    if ctrl is None:
        raise Exception("Jira client is not initialized")
    sample_task = search("filter = 'Tasks this month'")[0]
    if description is None or not isinstance(description, str):
        description = ""
    params = {
        "project": "GTD",
        "summary": summary,
        "description": description,
        "issuetype": {"name": "Task"},
    }
    if parent:
        params["parent"] = {"key": parent}
    if context:
        params[get_context_field(sample_task_key=sample_task.key)["key"]] = {"value": context}
    if duedate:
        params["duedate"] = duedate
    ticket = ctrl.create_issue(fields=params)
    return ticket

    
def retro(use_html: bool = False):
    tasks: list[Issue] = search("filter = 'weekly retro'")
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
        