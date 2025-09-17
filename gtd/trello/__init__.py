
import trello 
import os
import json  
import datetime 
from gtd.config import get_config_str
from gtd.style import *
from gtd.extensions import ReportService, load_extensions
from gtd.importer import Importer
from gtd.utils import ExponentialBackoff
from gtd.attachments import get_attachments_dir, attach_file
ai_enabled = True

this_week_label = get_config_str("trello_this_week_label", "This week", "Label Used in tasks in Trello to mark tasks for this week")

abandomed_label = get_config_str("trello_abandoned_label", "Abandoned", "Label Used in tasks in Trello to mark tasks that are abandoned")

try:
    from fantastixus_ai import get_action_points, load_credentials, get_help_with_task
except ImportError:
    def get_action_points(prompt, apikey):
        return []

    def load_credentials():
        return None
    ai_enabled = False

def utc_to_this_tz(utc_time: str) -> datetime.datetime:
    current_utc_time = datetime.datetime.utcnow()
    current_time = datetime.datetime.now()
    dt = current_time - current_utc_time
    try:
        return datetime.datetime.strptime(utc_time, "%Y-%m-%dT%H:%M:%S.%fZ") + dt
    except ValueError:
        print("Error parsing date: %s" % utc_time)
        return None

def CheckField(field):
    return lambda c: field in c and c[field] is not None and c[field]

def NotCheckField(field):
    return lambda c: not CheckField(field)(c)

backoff = ExponentialBackoff(base_delay=1, max_delay=60, max_retries=5)

class TrelloAPI:
    def __init__(self, apikey=None, token=None) -> None:
        """
        Initialize the Trello API. If apikey and token are not provided, they are read from the configuration file.

        :param apikey: Trello API key
        :param token: Trello token
        :raises ValueError: If the Trello API key is not set and not provided as an argument
        :raises ValueError: If the Trello token is not set and not provided as an argument
        :raises ValueError: If the Trello API key is invalid
        """
        
        if apikey is None:
            apikey = get_config_str("trello_apikey", "", "Trello API key")
        if apikey == "":
            raise ValueError("Trello API key not set")
        try:
            api = trello.TrelloApi(apikey=apikey)
        except json.JSONDecodeError:
            raise ValueError("Invalid Trello API key")
        if token is None:
            token = get_config_str("trello_token", "", "Trello token")
        if token == "":
            raise ValueError("Trello token not set")
        try:
            api.set_token(token)
        except json.JSONDecodeError:
            raise ValueError("Invalid Trello token")
        except Exception as e:
            raise ValueError("Error setting Trello token: %s" % e)
        self.api = api
        self.list_name = {} 

    @backoff
    def get_boards(self):
        try:
            return self.api.members.get_board('me')
        except Exception as e:
            print("Error getting boards: %s" % e)
            raise ValueError("Error getting boards")
    
    @backoff
    def get_board(self, board_name=None):
        if board_name is None:
            board_name = self.get_default_board()
        try:
            return next(b for b in self.get_boards() if b['name'] == board_name)
        except StopIteration:
            raise ValueError("Board not found: %s" % board_name)
        except KeyError:
            raise ValueError("Key 'name' not found in board, API probably changed")

    @backoff
    def get_default_board(self):
        """
        Get the default board name from the configuration file.

        :return: Default board name
        :raises ValueError: If the default board name is not set
        """
        boards = self.get_boards()
        if len(boards) == 0:
            raise ValueError("No boards found")
        board_name = get_config_str("trello_board", boards[0]['name'], "Trello board name")
        return board_name


    @backoff
    def get_lists(self, board_name=None):
        if board_name is None:
            board_name = self.get_default_board()
        board = self.get_board(board_name)
        try:
            return self.api.boards.get_list(board['id'])
        except Exception as e:
            print("Error getting lists: %s" % e)
            raise ValueError("Error getting lists")

    @backoff
    def get_open_cards(self, board_name=None):
        if board_name is None:
            board_name = self.get_default_board()
        board = self.get_board(board_name)
        try:
            return list(filter(NotCheckField("dueComplete"), self.api.boards.get_card(board['id'])))
        except Exception as e:
            print("Error getting cards: %s" % e)
            raise ValueError("Error getting cards")

    @backoff
    def get_closed_cards(self, board_name=None):
        if board_name is None:
            board_name = self.get_default_board()
        board = self.get_board(board_name)
        try:
            cards =  self.api.boards.get_card(board['id'], filter='closed') + list(filter(CheckField("dueComplete"), self.api.boards.get_card(board['id'])))
            return [c for c in cards if abandomed_label not in [l["name"] for l in c["labels"]]]
        except Exception as e:
            print("Error getting cards: %s" % e)
            raise ValueError("Error getting cards")

    @backoff
    def get_closed_lists(self, board_name=None):
        if board_name is None:
            board_name = self.get_default_board()
        board = self.get_board(board_name)
        try:
            return self.api.boards.get_list(board['id'], filter='closed')
        except Exception as e:
            print("Error getting lists: %s" % e)
            raise ValueError("Error getting lists")
    
    @backoff
    def get_list_name(self, card):
        try:
            if card['idList'] not in self.list_name:
                self.list_name[card['idList']] = self.api.lists.get(card['idList'])['name']
            return self.list_name[card['idList']]
        except KeyError:
            raise ValueError("Key 'name' not found in list, API probably changed, data: %s" % card)
        except Exception as e:
            print("Error getting list name: %s" % e)
            raise ValueError("Error getting list name")
    
    @backoff
    def get_checklist(self, card):
        try:
            if len(card['idChecklists']) == 0:
                return None
            return self.api.checklists.get(card['idChecklists'][0])
        except KeyError:
            raise ValueError("Key 'idChecklists' not found in card, API probably changed, data: %s" % card)
        except Exception as e:
            print("Error getting checklist: %s" % e)
            raise ValueError("Error getting checklist")
    
    @backoff
    def add_list(self, name, board_name=None):
        if board_name is None:
            board_name = self.get_default_board()
        board = self.get_board(board_name)
        try:
            return self.api.lists.new(name, board['id'])
        except Exception as e:
            print("Error creating list: %s" % e)
            raise ValueError("Error creating list")
    @backoff
    def add_card(self, name, list_id, desc=None, due=None):
        try:
            return self.api.cards.new(name, list_id, desc=desc, due=due)
        except Exception as e:
            print("Error creating card: %s" % e)
            raise ValueError("Error creating card")
    @backoff
    def add_checklist(self, card_id, name):
        try:
            return self.api.checklists.new(card_id, name)
        except Exception as e:
            print("Error creating checklist: %s" % e)
            raise ValueError("Error creating checklist")
    @backoff
    def add_checklist_item(self, checklist_id, name):
        try:
            return self.api.checklists.new_checkItem(checklist_id, name)
        except Exception as e:
            print("Error creating checklist item: %s" % e)
            raise ValueError("Error creating checklist item")
    
    @backoff
    def has_label(self, card, label_name):
        try:
            return any(l['name'] == label_name for l in card['labels'])
        except KeyError:
            raise ValueError("Key 'labels' not found in card, API probably changed, data: %s" % card)
        except Exception as e:
            print("Error checking label: %s" % e)
            raise ValueError("Error checking label")
    @backoff
    def remove_label(self, card, label_name):
        """
        Removes label from given card.
        """
        try:
            label = next(l for l in card['labels'] if l['name'] == label_name)
            self.api.cards.delete_idLabel_idLabel(label['id'], card['id'])
        except StopIteration:
            raise ValueError("Label not found: %s" % label_name)
        except KeyError:
            raise ValueError("Key 'labels' not found in card, API probably changed, data: %s" % card)
        except Exception as e:
            print("Error removing label: %s" % e)
            raise ValueError("Error removing label")
    
    @backoff
    def get_comments(self, card):
        """
        Returns comments from given card.
        """
        try:
            return [c["data"]["text"] for c in self.api.cards.get(card['id'], actions='commentCard')['actions'] if c['type'] == 'commentCard']
        except KeyError:
            raise ValueError("Key 'comments' not found in card, API probably changed, data: %s" % card)
        except Exception as e:
            print("Error getting comments: %s" % e)
            raise ValueError("Error getting comments")

    @backoff
    def attach(self, card, title, markdown_content):
        """
        Attaches HTML to given card.
        """
        attachments_dir = get_attachments_dir()
        attachment_path = os.path.join(attachments_dir, title + ".html")
        if not os.path.exists(attachments_dir):
            os.makedirs(attachments_dir)
        try:
            from markdown_it import MarkdownIt

            md = MarkdownIt("commonmark", {"html": True}) \
                .enable("table")  

            content = md.render(markdown_content)
            content = """

<html>
<head>
    <meta charset="utf-8">

<script>
MathJax = {
  tex: {
    inlineMath: [['$', '$'], ['\\\\(', '\\\\)']]
  },
  svg: {
    fontCache: 'global'
  }
};
</script>
<script type="text/javascript" id="MathJax-script" async
  src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-svg.js">
</script>
    

</head>
<body>
    <h1>%s</h1>
    %s

    <p>Generated by Fantastixus</p>
</body>
</html>

""" % (title, content)
            
            with open(attachment_path, "w") as f:
                f.write(content)
            self.api.cards.new_attachment(card['id'], open(attachment_path).read(), mimeType="text/html", name=title + ".html")

        except ImportError:
            print("Error importing markdown-it-py or mdit-py-plugins")
            content = markdown_content
            try:
                with open(attachment_path, "w") as f:
                    f.write(content)
                self.api.cards.new_attachment(card['id'], open(attachment_path).read(), mimeType="text/plain", name=title + ".md")
            except Exception as e:
                print("Error attaching HTML: %s" % e)
                raise ValueError("Error attaching HTML")
        return attachment_path

    @backoff
    def get_creation_date(self, card):
        """
        Returns the creation date of the given card.
        """
        try:
            card_id = card['id']
            # First 8 chars = timestamp (hex)
            ts_hex = card_id[:8]
            ts_int = int(ts_hex, 16)
            created_at = datetime.datetime.utcfromtimestamp(ts_int)
            return created_at
        except Exception as e:
            raise ValueError("Error getting creation date: %s" % e)

def generate_report():
    result = [] 
    ai_help_label = get_config_str("trello_ai_help_label", "Help", "Label Used in tasks in Trello to mark tasks for AI help")
    result.append("<!DOCTYPE html>")
    result.append("<html>")
    result.append("<head>")
    result.append("<meta charset='utf-8'>")
    result.append("</head>")

    result.append("<body>")
    result.append("<h1>Trello Report</h1>")
    try:
        api = TrelloAPI()
        backlog = api.get_lists()
        open_cards = api.get_open_cards()
        this_week = [c for c in open_cards if this_week_label in [l["name"] for l in c["labels"]]]

        card_to_list = {}
        for c in this_week:
            list_name = api.get_list_name(c)
            if list_name not in card_to_list:
                card_to_list[list_name] = []
            card_to_list[list_name].append(c)


        result.append(section("Tickets this week with checklist"))
        for mylist, cards in card_to_list.items():
            cards = list([c for c in cards if CheckField("idChecklists")(c)])
            if len(cards) == 0:
                continue
            result.append(section(mylist, level=1))
            result.append(items([ticket(c) for c in cards]))

        result.append(section("Tickets this week without checklist"))
        for mylist, cards in card_to_list.items():
            cards = list([c for c in cards if NotCheckField("idChecklists")(c)])
            if len(cards) == 0:
                continue
            result.append(section(mylist, level=1))
            apikey = load_credentials()
            for c in cards:
                result.append(paragraph(ticket(c)))
                task_description = "" 
                task_description += "Title: %s\n" % c["name"]
                task_description += "Description: %s\n" % c["desc"]
                task_description += "Project: %s\n" % api.get_list_name(c)
                task_description += "Action points should be doable in 30 minutes each.\n"
                task_description += "Please provide a list of at most 7 action points.\n"
                suggestions = get_action_points(task_description, apikey)
                
                if len(suggestions) > 0:
                    result.append(items([s for s in suggestions]))
                    checklist = api.add_checklist(c["id"], "Checklist")
                    for s in suggestions:
                        api.add_checklist_item(checklist["id"], s)
                else:
                    result.append(paragraph("No suggestions found"))
        closed_cards = api.get_closed_cards()
        number_closed_cards = len(closed_cards)
        # first day is day when we created first card

        first_day = None
        for c in open_cards + closed_cards:
            if first_day is None:
                first_day = datetime.datetime.strptime(c["dateLastActivity"], "%Y-%m-%dT%H:%M:%S.%fZ").date()
            else:
                if datetime.datetime.strptime(c["dateLastActivity"], "%Y-%m-%dT%H:%M:%S.%fZ").date() < first_day:
                    first_day = datetime.datetime.strptime(c["dateLastActivity"], "%Y-%m-%dT%H:%M:%S.%fZ").date()
        if first_day is None:
            first_day = datetime.datetime.now().date()
        if number_closed_cards == 0:
            result.append(paragraph("No cards closed yet. Please close some cards to see statistics."))
            return "\n".join(result)
        days_passed = 1 + (datetime.datetime.now().date() - first_day).days
        if days_passed == 0:
            days_passed = 1
        result.append(section("Statistics"))
        result.append(paragraph("Average cards closed per day: %.2f" % (number_closed_cards / days_passed)))
        start_of_week = datetime.datetime.now() - datetime.timedelta(days=datetime.datetime.now().weekday())
        start_of_week = start_of_week.date()
        result.append(paragraph("Number of open cards: %d" % len(open_cards)))
        today = datetime.datetime.now().date()
        remaining_days = 1 + (datetime.date(today.year, 12, 31) - today).days
        result.append(paragraph("Remaining days in year: %d" % remaining_days))
        result.append(paragraph("Required closed tasks per day: %.2f" % ((len(open_cards)) / remaining_days)))
        result.append(paragraph("Start of week: %s" % start_of_week))
        result.append(
            paragraph(
                "If you continue with this closing rate, all tasks will be closed by %s" % (
                    (datetime.datetime.now().date() + datetime.timedelta(days=(len(open_cards) / (number_closed_cards / days_passed)))).strftime("%Y-%m-%d")
                )
            )
        )
        result.append(
            paragraph(
                "If you continue with closing rate 1 per day, all tasks will be closed by %s" % (
                    (datetime.datetime.now().date() + datetime.timedelta(days=(len(open_cards)))).strftime("%Y-%m-%d")
                )
            )
        )
        
        closed_this_week = list([c for c in closed_cards if datetime.datetime.strptime(c["dateLastActivity"], "%Y-%m-%dT%H:%M:%S.%fZ").date() >= start_of_week])
        opened_this_week = list([c for c in open_cards if api.get_creation_date(c).date() >= start_of_week])
        result.append(paragraph("Cards opened this week: %d" % len(opened_this_week)))
        result.append("Net closure this week: %d" % (len(closed_this_week) - len(opened_this_week)))
        list_to_closed_cards = {}
        for c in closed_this_week:
            list_name = api.get_list_name(c)
            if list_name not in list_to_closed_cards:
                list_to_closed_cards[list_name] = []
            list_to_closed_cards[list_name].append(c)
        if len(closed_this_week) > 0:
            result.append(paragraph("Last card closed on %s" % api.get_closed_cards()[0]["dateLastActivity"]))
        result.append(paragraph("Cards closed this week: %d" % len(closed_this_week)))
        result.append(section("Closed cards this week"))
        for list_name, closed_cards in list_to_closed_cards.items():
            result.append(section(list_name, level=1))
            result.append(items([ticket(c) for c in closed_cards]))
        result.append(section("Number of open cards per list"))
        data_table = [] 
        open_cards
        for l in backlog:
            data_table.append({
                "List": l["name"],
                "Number of open cards": len([c for c in open_cards if c["idList"] == l["id"]])
            })
        df = pd.DataFrame(data_table)
        df["Cuumulative"] = df["Number of open cards"].cumsum()
        result.append(table(df))

        result += load_extensions()
    except ValueError as e:
        result.append(error("%s" % e))
    result.append("</body>")
    result.append("</html>")
    if ai_enabled:
        ai_help(api, open_cards, ai_help_label)
    return "\n".join(result)

def ai_help(api: TrelloAPI, cards, ai_help_label):
    api_key = load_credentials()
    for card in cards:
        if api.has_label(card, ai_help_label):
            project = api.get_list_name(card)
            title = card["name"]
            description = card.get("desc", "")
            checklist = []
            if CheckField("idChecklists")(card):
                checklist = api.get_checklist(card)
                checklist = checklist["checkItems"]
                checklist = [c["name"] for c in checklist if c["state"] == "incomplete"]
            comments = api.get_comments(card)

            attachment_name = f"{project} - {title}"
            api.remove_label(card, ai_help_label)
            print("Removed label %s from card %s" % (ai_help_label, attachment_name))
            response = get_help_with_task(api_key, project, title, description, checklist or None, comments or None)
            api.attach(card, attachment_name, response)
            print("Attached response to card %s" % attachment_name)

class TrelloImporter(Importer):

    def __init__(self):
        self.api = TrelloAPI()

    def list_projects(self):
        return [l["name"].strip() for l in self.api.get_lists()]

    def create(self, title, description, due_date = None, context = None, project = None, checklists = None):
        print("""
              Creating a new card in Trello:
                Title: %s
                Description: %s
                Due date: %s
                Context: %s
                Project: %s
                Checklist: %s
                """ % (title, description, due_date, context, project, checklists)
        )
        if project is None:
            project = self.list_projects()[0]
        else:
            project = project.strip()
        if project not in self.list_projects():
            print("Project %s not found, creating it" % project)
            self.api.add_list(project)
        list_id = next(l for l in self.api.get_lists() if l["name"].strip() == project)["id"]
        card = self.api.add_card(title, list_id, desc=description, due=due_date)
        if checklists is not None and len(checklists.keys()) > 0:
            for checklist_name, checklist_items in checklists.items():
                if len(checklist_items) > 0:
                    checklist_id = self.api.add_checklist(card["id"], checklist_name)["id"]
                    for item in checklist_items:
                        self.api.add_checklist_item(checklist_id, item)
        print("Card created: %s" % card["shortUrl"])
        return card["shortUrl"]

    def create_project(self, name):
        self.api.add_list(name)
    
    def exists(self, title, description = None, due_date = None, context = None, project = None):
        """
        Check if a card with the given title exists in Trello in given project.

        :param title: Title of the card
        :param description: Description of the card
        :param due_date: Due date of the card
        :param context: Context of the card
        :param project: Project of the card
        :return: True if the card exists, False otherwise
        """
        if project is None:
            project = self.list_projects()[0]
        list_id = next(iter([l for l in self.api.get_lists() if l["name"] == project]), {"id": None})["id"]
        if list_id is None:
            return False 
        cards = self.api.get_open_cards()
        for card in cards:
            if card["name"] == title and card["idList"] == list_id:
                return True
        return False

    def list_all_open_tasks(self) -> list[dict]:
        cards = self.api.get_open_cards()
        result = []
        for c in cards:
            checklist = None
            if CheckField("idChecklists")(c):
                checklist = self.api.get_checklist(c)
                if checklist is not None:
                    checklist = checklist["checkItems"]
                    checklist = [ci["name"] for ci in checklist]
            result.append({
                "title": c["name"],
                "description": c.get("desc", ""),
                "due_date": utc_to_this_tz(c["due"]) if c["due"] else None,
                "project": self.api.get_list_name(c),
                "creation_date": self.api.get_creation_date(c),
                "checklists": {
                    "Checklist": checklist
                } if checklist else []
            })
        return result    

    def list_all_closed_tasks(self) -> list[dict]:
        cards = self.api.get_closed_cards()
        result = []
        for c in cards:
            checklist = None
            if CheckField("idChecklists")(c):
                checklist = self.api.get_checklist(c)
                if checklist is not None:
                    checklist = checklist["checkItems"]
                    checklist = [ci["name"] for ci in checklist]
            result.append({
                "title": c["name"],
                "description": c.get("desc", ""),
                "due_date": utc_to_this_tz(c["due"]) if c["due"] else None,
                "project": self.api.get_list_name(c),
                "creation_date": self.api.get_creation_date(c),
                "closure_date": utc_to_this_tz(c["dateLastActivity"]) if c["dateLastActivity"] else None,
                "checklists": {
                    "Checklist": checklist
                } if checklist else []
            })
        return result
    

def generate_retro_report(year, week, start=-1):
    """
    Week is specified as calendar week, starting from 1.

    :param year: Year number
    :param week: Week number
    :param start: Generate report starting from this week (default: -1, means same as week)
    :return: HTML report
    """
    if start == -1:
        start = week
    week_first_day = datetime.datetime.strptime(f"{year}-W{start}-1", "%Y-W%W-%w").date()
    week_last_day = datetime.datetime.strptime(f"{year}-W{week}-0", "%Y-W%W-%w").date()
    result = [] 
    result.append("<!DOCTYPE html>")
    result.append("<html>")
    result.append("<head>")
    result.append("<meta charset='utf-8'>")
    result.append("</head>")

    result.append("<body>")
    result.append("<h1>Trello Report</h1>")
    try:
        api = TrelloAPI()
        closed_cards = api.get_closed_cards()

        this_week = [c for c in closed_cards if datetime.datetime.strptime(c["dateLastActivity"], "%Y-%m-%dT%H:%M:%S.%fZ").date() >= week_first_day and datetime.datetime.strptime(c["dateLastActivity"], "%Y-%m-%dT%H:%M:%S.%fZ").date() <= week_last_day]
        card_to_list = {}
        for c in this_week:
            list_name = api.get_list_name(c)
            if list_name not in card_to_list:
                card_to_list[list_name] = []
            card_to_list[list_name].append(c)

        result.append(section("Closed cards per list"))
        for mylist, cards in card_to_list.items():
            result.append(section(mylist, level=1))
            result.append(items([ticket(c) for c in cards]))
        result.append(section("Statistics"))
        number_closed_cards = len(closed_cards)
        result.append(paragraph("First day of week: %s" % week_first_day))
        result.append(paragraph("Last day of week: %s" % week_last_day))
        result.append(paragraph("Closed cards this week: %d" % len(this_week)))
    except Exception as e:
        result.append(error("%s" % e))
    result.append("</body>")
    result.append("</html>")
    return result

class TrelloOpenCards(ReportService):
    """
    Provides a report of open cards in Trello.
    """

    def provide(self):
        result = [] 
        try:
            api = TrelloAPI()
            open_cards = api.get_open_cards()
            return [{
                "title": c["name"],
                "description": c.get("desc", ""),
                "due_date": utc_to_this_tz(c["due"]) if c["due"] else None,
                "project": api.get_list_name(c),
                "url": c["shortUrl"],
                "labels": [l["name"] for l in c["labels"]],
                "id": c["id"],
            } for c in open_cards]
        except:
            return {
                "error": "Error getting open cards from Trello. Please check your configuration and API key."
            }

class TrelloClosedCards(ReportService):
    """
    Provides a report of closed cards in Trello.
    """

    def provide(self):
        result = [] 
        try:
            today = datetime.datetime.now().date()
            api = TrelloAPI()
            closed_cards = api.get_closed_cards()
            return [{
                "title": c["name"],
                "description": c.get("desc", ""),
                "due_date": utc_to_this_tz(c["due"]) if c["due"] else None,
                "project": api.get_list_name(c),
                "url": c["shortUrl"],
                "labels": [l["name"] for l in c["labels"]],
                "id": c["id"],
                "closed_date": utc_to_this_tz(c["dateLastActivity"]) if c["dateLastActivity"] else None,
                "closed_from_today": (today - utc_to_this_tz(c["dateLastActivity"]).date()).days if c["dateLastActivity"] else None,
            } for c in closed_cards]
        except Exception as e:
            return {
                "error": "Error getting closed cards from Trello. Please check your configuration and API key.",
                "details": str(e)
            }

class TrelloThisWeekCards(ReportService):
    """
    Provides a report of cards for this week in Trello.
    """

    def provide(self):
        result = [] 
        try:
            api = TrelloAPI()
            open_cards = api.get_open_cards()
            this_week = [c for c in open_cards if this_week_label in [l["name"] for l in c["labels"]]]
            return [{
                "title": c["name"],
                "description": c.get("desc", ""),
                "due_date": utc_to_this_tz(c["due"]) if c["due"] else None,
                "project": api.get_list_name(c),
                "url": c["shortUrl"],
                "labels": [l["name"] for l in c["labels"]],
                "id": c["id"],
            } for c in this_week]
        except:
            return {
                "error": "Error getting cards for this week from Trello. Please check your configuration and API key."
            }

class TrelloThisWeekNetClosure(ReportService):
    """
    Provides info about net closure of cards this week.
    """
    def provide(self):
        result = {} 
        try:
            today = datetime.datetime.now().date()
            start_of_week = today - datetime.timedelta(days=6)
            api = TrelloAPI()
            closed_cards = api.get_closed_cards()
            all_cards = api.get_open_cards() + closed_cards
            open_this_week = [c for c in all_cards if api.get_creation_date(c).date() >= start_of_week]
            closed_this_week = list([c for c in closed_cards if datetime.datetime.strptime(c["dateLastActivity"], "%Y-%m-%dT%H:%M:%S.%fZ").date() >= start_of_week])
            result["open_this_week"] = len(open_this_week)
            result["closed_this_week"] = len(closed_this_week)
            result["net_closure"] = len(closed_this_week) - len(open_this_week)
            return result
        except Exception as e:
            return {
                "error": "Error getting net closure from Trello. Please check your configuration and API key.",
                "details": str(e)
            }