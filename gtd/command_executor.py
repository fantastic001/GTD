import pandas as pd 
from gtd.config import * 
from gtd.style import * 
from gtd.config import get_classes_inheriting
from gtd.importer import Importer, import_task

@pluggable
def generate_report():
    return None 
class CommandExecutor:

    def importers(self):
        return get_classes_inheriting(Importer)

    def report(self):
        """
        Creates report of tasks and other information from plugins in HTML page. 

        When called from CLI, HTML content is printed to stdout.
        When called from Python, HTML content is returned as string.
        """
        custom_report = generate_report()
        if custom_report is not None:
            return custom_report
        return ""

    def projects(self, *, importer: str = ""):
        """
        Lists all projects available in the specified importer. If no importer is specified, it returns the first one found.
        """
        importer: Importer = self.get_importer(importer=importer)
        return importer.list_projects()

    def get_importer(self, *, importer: str = "") -> Importer:
        """
        Returns the importer class specified by the user. If no importer is specified, it returns the first one found.
        """
        importers = self.importers()
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
                else:
                    raise Exception("Error occurred while creating ticket: %s" % line)

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
                else:
                    raise Exception("Error occurred while creating ticket: %s" % summary)
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
                else:
                    raise Exception("Error occurred while creating ticket: %s" % summary)



    def usage(self):
        return """
        Usage: gtd COMMAND [ARGS]
        Commands:
        - report: Generates a report of tasks and other information from plugins in HTML page.
        - projects: Lists all projects available in the specified importer. If no importer is specified, it returns the first one found.
        - create_ticket: Creates a new ticket with the specified parameters.
        - import_csv: Imports a csv file with the specified columns.
        - upload: Uploads a batch of tasks in text specified.
        

        For more information about a command, use gtd COMMAND --help
        """
    def examples(self):
        return """
        Examples:
        - gtd report
        - gtd create_ticket --summary "Test" --context "Work" --duedate "2021-10-10" --parent "GTD-1"
        - gtd import_csv --path tasks.csv

        Importing:

        If you have file with this content:
        Task 1
        Task 2
        Task 3

        You can import it with:
        gtd upload --input tasks.txt

        If you have file with this content:
        Task 1
        Description

        Task 2
        Description

        You can import it with:
        gtd upload --input tasks.txt --multiline

        If you have file with this content:

        Task 1
        Description
        * Checklist item 1
        * Checklist item 2

        Task 2
        Description
        * Checklist item 1
        * Checklist item 2

        You can import it with:
        gtd upload --input tasks.txt --checklists
        """
    