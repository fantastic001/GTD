from dataclasses import asdict, field, fields
import datetime
from typing import Any
from urllib.parse import non_hierarchical
import pandas as pd 
import jira
import json 
import os
import requests 
from gtd.drive import Spreadsheet
from gtd.config import * 
from jira.resources import Issue 
from gtd.style import * 
from gtd.extensions import load_extensions
from gtd.config import get_classes_inheriting
from gtd.importer import Importer, import_task

@pluggable
def generate_report():
    return None 



class CommandExecutor:
    
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
        custom_report = generate_report()
        if custom_report is not None:
            return custom_report
        return ""

    def get_importer(self, *, importer: str = "") -> Importer:
        """
        Returns the importer class specified by the user. If no importer is specified, it returns the first one found.
        """
        importers = get_classes_inheriting(Importer)
        if len(importers) == 0:
            raise Exception("No importers available")
        elif len(importers) > 1 and importer == "":
            raise Exception("Multiple importers available. Please specify one.")
        elif len(importers) == 1 and importer == "":
            importer = importers[0]
        elif importer not in [i.__name__ for i in importers]:
            raise Exception("Importer %s not found" % importer)
        else:
            importer = [i for i in importers if i.__name__ == importer][0]
        return importer()


    def create_ticket(self, summary, *, parent: str = "", description = "", context: str = "", duedate: str = "", importer: str = ""):
        """
        Example: gtd create_ticket --summary "Test" --context "Work" --duedate "2021-10-10" --parent "GTD-1"
        """
        import_task(
            importer=self.get_importer(importer=importer),
            summary=summary,
            project=parent,
            description=description,
            context=context,
            due_date=duedate,
            unique=True,
        )


    def import_csv(self, path: str):
        """
        Imports a csv file with the following columns:
        - Summary
        - Context
        - Due date
        - Parent
        - Description

        Example: gtd import_csv tasks.csv
        """
        df = pd.read_csv(path)
        for i, row in df.iterrows():
            ticket = self.create_ticket(
                summary=row["Summary"],
                context=row["Context"],
                duedate=row["Due date"],
                parent=row["Parent"],
                description=row["Description"]
            )
            print("Created ticket: %s" % ticket.key)
    
    def upload(self, *, input: str = "", multiline: bool = False, checklists: bool = False, importer: str = "", parent: str = ""):
        """
        Uploads batch of tasks in text specified. 


        :param input: Path of file to read from. If left to default, stdin is used.
        :param multiline: If True, First line is title, rest is description. Tasks are separated by empty line.
        :param checklists: If True, every line after title which starts with "*" is a checklist item for that task.
        :param importer: If specified, use this importer to upload tasks. If not specified, then:
            if multiple importers are available, command will fail. 
            If none importer is available, command will fail.
            If only one importer is available, it will be used.
        :param parent: If specified, use this parent for all tasks. If not specified, use first found.
        """
        importer: Importer = self.get_importer(importer=importer)
        available_parents = importer.list_projects()
        if checklists:
            # if using checklists, multiline behavior is assumed so we can safely turn it off
            multiline = False
        if parent != "" and parent not in available_parents:
            print("Parent %s not found. Creating it." % parent)
            importer.create_project(parent)
        elif parent == "":
            parent = available_parents[0]
        if input == "":
            input_f = sys.stdin
        else:
            input_f = open(input, "r")
        if not multiline and not checklists:
            for line in input_f:
                line = line.strip()
                if line == "":
                    continue
                if import_task(
                    importer=importer,
                    title=line,
                    project=parent,
                    unique=True,
                ):
                    print("Created ticket: %s" % line)
        elif multiline and not checklists:
            summary = ""
            description = ""
            for line in input_f:
                line = line.strip()
                if line == "":
                    if summary != "":
                        if import_task(
                            importer=importer,
                            title=summary,
                            description=description,
                            project=parent,
                            unique=True,
                        ):
                            print("Created ticket: %s" % summary)
                    summary = ""
                    description = ""
                elif summary == "":
                    summary = line
                else:
                    description += line + "\n"
            if summary != "":
                if import_task(
                    importer=importer,
                    title=summary,
                    description=description,
                    project=parent,
                    unique=True,
                ):
                    print("Created ticket: %s" % summary)
        elif not multiline and checklists:
            summary = ""
            description = ""
            checklists = []
            for line in input_f:
                line = line.strip()
                if line == "":
                    if summary != "":
                        if import_task(
                            importer=importer,
                            title=summary,
                            description=description,
                            project=parent,
                            checklist=checklists,
                            unique=True,
                        ):
                            print("Created ticket: %s" % summary)
                    summary = ""
                    description = ""
                    checklists = []
                elif summary == "":
                    summary = line
                elif line.startswith("*"):
                    checklists.append(line[1:].strip())
                else:
                    description += line + "\n"
            if summary != "":
                if import_task(
                    importer=importer,
                    title=summary,
                    description=description,
                    project=parent,
                    checklist=checklists,
                    unique=True,
                ):
                    print("Created ticket: %s" % summary)



    def usage(self):
        return """
        Usage: gtd COMMAND [ARGS]
        Commands:
        - search
        - report
        - create_ticket
        - import_csv

        For more information about a command, use gtd COMMAND --help
        """
    def examples(self):
        return """
        Examples:
        - gtd search --jql "filter = 'Tasks this month'"
        - gtd report
        - gtd create_ticket --summary "Test" --context "Work" --duedate "2021-10-10" --parent "GTD-1"
        - gtd import_csv --path tasks.csv
        """
    