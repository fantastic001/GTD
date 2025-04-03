
from gtd.extensions import Report
from gtd.config import get_config_str, get_config_bool
from gtd.drive import Spreadsheet
import datetime
from gtd.style import section, table, paragraph, items
import os 
from markdown_it import MarkdownIt


def add_extensions(report: Report):
    """
    Reads README.md files from notes and prepares random section to do exercise  for given week
    """
    notes_path = get_config_str("notes_path", "/data/Development/notes/", "Path to notes directory")
    notes_path = os.path.expanduser(notes_path)
    year, week = datetime.datetime.now().isocalendar()[:2]
    n = year * 100 + week
    n = hash(n)
    readme_files = [] 
    for root, dirs, files in os.walk(notes_path):
        for file in files:
            if file == "README.md":
                readme_files.append(os.path.join(root, file))
    for readme in readme_files:
        if len(os.path.dirname(readme).split(notes_path)) < 2:
            continue
        basedir = os.path.dirname(readme).split(notes_path)[1]
        # read the file and convert to markdown
        with open(readme, "r") as f:
            content = f.read()
        md = MarkdownIt()
        tokens = md.parse(content)
        sections = []
        for token in tokens:
            if token.type == "heading_open":
                # get the heading level
                level = int(token.tag[1:])
                # get the heading text
                heading = tokens[tokens.index(token) + 1].content
                if level == 1:
                    sections.append("%s - %s" % (basedir, heading))
    week_section = sections[n % len(sections)]
    report.add(section("Exercise section"))
    report.add(paragraph("This week we will work on %s" % week_section))