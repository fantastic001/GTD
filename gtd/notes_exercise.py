
import subprocess
from gtd.extensions import Report
from gtd.config import get_config_str, get_config_bool
from gtd.drive import Spreadsheet
import datetime
from gtd.style import section, table, paragraph, items
import os 
from markdown_it import MarkdownIt
import hashlib
from gtd.attachments import attach_file

ai_enabled = False 

try:
    from fantastixus_ai import load_credentials, get_chatgpt_response
    ai_enabled = True 
except ImportError as e:
    print("fanastixus_ai not installed. AI features will be disabled.")
    print(e)
    pass

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
                    sections.append((basedir, heading))
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
    report.add(paragraph("This week we will work on %s - %s" % week_section))
    if ai_enabled:
        challange = generate_weekly_challange(week_section[0], week_section[1])
        report.add(paragraph("AI generated weekly challange attached below."))
        attach_file(challange)
        


def generate_weekly_challange(field: str, topic: str):
    prompt = f"""

        Give some fun and challanging exercise to work whole week from {field} with focus on {topic}

        Use mathematical notation if needed. Provide the response in markdown format.

    """
    challange_cache_path = get_config_str("challange_cache_path", os.path.expanduser("~/.cache/gtd/challanges/"), "Path to challange cache directory")
    os.makedirs(challange_cache_path, exist_ok=True)
    # clean entries in cache with mtime older than 10 days
    now = datetime.datetime.now().timestamp()
    for file in os.listdir(challange_cache_path):
        file_path = os.path.join(challange_cache_path, file)
        if os.path.isfile(file_path):
            mtime = os.path.getmtime(file_path)
            if now - mtime > 10 * 24 * 3600:
                os.remove(file_path)
    entries = [os.path.join(challange_cache_path, f) for f in os.listdir(challange_cache_path) if os.path.isfile(os.path.join(challange_cache_path, f))]
    latest_entry = None
    if len(entries) > 0:
        latest_entry = max(entries, key=os.path.getmtime)
    # if latest entry is older than 7 days, generate new one
    day_of_week = datetime.datetime.now().weekday()  # Monday is 0 and Sunday is 6
    if latest_entry is None or (now - os.path.getmtime(latest_entry)) > 7 * 24 * 3600 or day_of_week == 0:
        apikey = load_credentials()
        new_entry = os.path.join(challange_cache_path, f"challange_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf")
        # check if pandoc is installed
        if os.system("pandoc --version > /dev/null 2>&1") != 0:
            raise RuntimeError("pandoc is not installed. Please install pandoc to use AI features.")
        response: str = get_chatgpt_response(prompt, apikey)
        response = response.replace("\\[", "$$").replace("\\]", "$$")
        response = response.replace("\\(", "$").replace("\\)", "$")
        
        proc = subprocess.Popen(["pandoc", "-o", new_entry, "-f", "markdown+tex_math_dollars+tex_math_double_backslash"], stdin=subprocess.PIPE)
        proc.communicate(input=response.encode("utf-8"))
        return new_entry
    else:
        return latest_entry
if __name__ == "__main__":
    sections = get_sections()
    print("Sections found:")
    for section in sections:
        print(section)
    print("Total number of sections: %d" % len(sections))
    print("Lucky number: %d" % get_lucky_number())
    field, topic = sections[get_lucky_number() % len(sections)]
    print("This week we will work on %s - %s" % (field, topic))
    if ai_enabled:
        print("AI generated weekly challange:")
        print(generate_weekly_challange(field, topic))
    else:
        print("AI not enabled. Please install fanastixus_ai package and set up credentials.")
    
