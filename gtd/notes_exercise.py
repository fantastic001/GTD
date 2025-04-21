
from gtd.extensions import Report
from gtd.config import get_config_str, get_config_bool
from gtd.drive import Spreadsheet
import datetime
from gtd.style import section, table, paragraph, items
import os 
from markdown_it import MarkdownIt
import hashlib

def get_sections():
    notes_path = get_config_str("notes_path", "/data/Development/notes/", "Path to notes directory")
    notes_path = os.path.expanduser(notes_path)
    readme_files = [] 
    sections = [] 
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
        for token in tokens:
            if token.type == "heading_open":
                # get the heading level
                level = int(token.tag[1:])
                # get the heading text
                heading = tokens[tokens.index(token) + 1].content
                if level == 1:
                    sections.append("%s - %s" % (basedir, heading))
    return sections

def get_lucky_number():
    year, week = datetime.datetime.now().isocalendar()[:2]
    n = year * 100 + week
    n = int.from_bytes(hashlib.md5(n.to_bytes(4, "big", signed=False)).digest()[:4], "big", signed=False)
    return n 

def add_extensions(report: Report):
    """
    Reads README.md files from notes and prepares random section to do exercise  for given week
    """
    sections = get_sections()
    if len(sections) == 0:
        report.add(paragraph("No sections found. Please check your notes directory and configuration."))
        return
    
    report.add(section("Exercise section"))
    luck_number = get_lucky_number() % len(sections)
    report.add(paragraph("Total number of sections: %d" % len(sections)))
    report.add(paragraph("Your lucky number is %d" % luck_number))
    week_section = sections[luck_number]
    report.add(paragraph("This week we will work on %s" % week_section))

if __name__ == "__main__":
    sections = get_sections()
    print("Sections found:")
    for section in sections:
        print(section)
    print("Total number of sections: %d" % len(sections))
    print("Lucky number: %d" % get_lucky_number())
    print("This week we will work on %s" % sections[get_lucky_number() % len(sections)])