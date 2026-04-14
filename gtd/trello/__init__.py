
from pprint import pprint
import re
import trello 
import os
import json  
import datetime 
from gtd.config import get_config_bool, get_config_list, get_config_str
from gtd.style import *
from gtd.extensions import ReportService, load_extensions
from gtd.importer import Importer
from gtd.utils import ExponentialBackoff
from gtd.attachments import get_attachments_dir, attach_file
from gtd.drive import get_context_for_project

import logging

logger = logging.getLogger(__name__)

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
            logger.error("Trello token not set. Please set the Trello token in the configuration file or provide it as an argument.")
            raise ValueError("Trello token not set")
        try:
            logger.info("Setting Trello token")
            api.set_token(token)
            logger.info("Trello token set successfully")
        except json.JSONDecodeError:
            logger.error("Invalid Trello token")
            raise ValueError("Invalid Trello token")
        except Exception as e:
            logger.error("Error setting Trello token: %s", e)
            raise ValueError("Error setting Trello token: %s" % e)
        self.api = api
        self.list_name = {} 

    @backoff
    def get_boards(self):
        try:
            logger.info("Getting boards")
            return self.api.members.get_board('me')
        except Exception as e:
            logger.error("Error getting boards: %s", e)
            raise ValueError("Error getting boards")
    
    @backoff
    def get_board(self, board_name=None):
        if board_name is None:
            logger.info("Getting default board")
            board_name = self.get_default_boards()[0]
        try:
            logger.info("Getting board with name: %s", board_name)
            return next(b for b in self.get_boards() if b['name'] == board_name)
        except StopIteration:
            logger.error("Board not found: %s", board_name)
            raise ValueError("Board not found: %s" % board_name)
        except KeyError:
            logger.error("Key 'name' not found in board, API probably changed")
            raise ValueError("Key 'name' not found in board, API probably changed")

    @backoff
    def get_default_boards(self):
        """
        Get the default board name from the configuration file.

        :return: Default board name
        :raises ValueError: If the default board name is not set
        """
        logger.info("Getting default board(s)")
        board_name = get_config_str("trello_board", "", "Trello board name")
        if board_name == "":
            logger.info("Default board name not set, trying to get it from trello_boards")
            boards = get_config_list("trello_boards", [], "Trello board names")
            if len(boards) == 0:
                logger.error("Trello board name not set or no boards available so cannot determine default board(s)")
                raise ValueError("Trello board name not set or no boards available so cannot determine default board(s)")
            logger.info("Default boards: %s", boards)
            return boards
        else:
            return [board_name]


    @backoff
    def get_lists(self, board_name=None):
        logger.info("Getting lists for board: %s", board_name if board_name else "all boards")
        if board_name is None:
            board_names = self.get_default_boards()
            return sum([self.get_lists(board_name=b) for b in board_names], [])
        board = self.get_board(board_name)
        try:
            return self.api.boards.get_list(board['id'])
        except Exception as e:
            logger.error("Error getting lists: %s", e)
            raise ValueError("Error getting lists")

    @backoff
    def get_open_cards(self, board_name=None):
        logger.info("Getting open cards for board: %s", board_name if board_name else "all boards")
        if board_name is None:
            board_names = self.get_default_boards()
            result =  sum(
                [self.get_open_cards(board_name=b) for b in board_names],
                []
            )
            logger.info("Got %d open cards for all boards", len(result))
            return result
        board = self.get_board(board_name)
        try:
            result = list(filter(NotCheckField("dueComplete"), self.api.boards.get_card(board['id'])))
            logger.info("Got %d open cards for board %s", len(result), board_name)
            return result

        except Exception as e:
            logger.error("Error getting cards: %s", e)
            raise ValueError("Error getting cards")

    @backoff
    def get_closed_cards(self, board_name=None):
        logger.info("Getting closed cards for board: %s", board_name if board_name else "all boards")
        if board_name is None:
            board_names = self.get_default_boards()
            result = sum(
                [self.get_closed_cards(board_name=b) for b in board_names], []
            )
            logger.info("Got %d closed cards for all boards", len(result))
            return result
        board = self.get_board(board_name)
        try:
            cards =  self.api.boards.get_card(board['id'], filter='closed') + list(filter(CheckField("dueComplete"), self.api.boards.get_card(board['id'])))
            result =  [c for c in cards if abandomed_label not in [l["name"] for l in c["labels"]]]
            logger.info("Got %d closed cards for board %s", len(result), board_name)
            return result
        except Exception as e:
            logger.error("Error getting cards: %s", e)
            raise ValueError("Error getting cards")

    @backoff
    def get_closed_lists(self, board_name=None):
        logger.info("Getting closed lists for board: %s", board_name if board_name else "all boards")
        if board_name is None:
            board_names= self.get_default_boards()
            return sum(
                [self.get_closed_lists(board_name=b) for b in board_names],
                []
            )
        board = self.get_board(board_name)
        try:
            result = self.api.boards.get_list(board['id'], filter='closed')
            logger.info("Got %d closed lists for board %s", len(result), board_name)
            return result
        except Exception as e:
            logger.error("Error getting lists: %s", e)
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
            logger.error("Error getting list name: %s", e)
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
            logger.error("Error getting checklist: %s", e)
            raise ValueError("Error getting checklist")
    
    @backoff
    def add_list(self, name, board_name=None):
        logger.info("Adding list with name: %s to board: %s", name, board_name if board_name else "default board")
        if board_name is None:
            board_names = self.get_default_boards()
            return self.add_list(name, board_name=board_names[0])
        board = self.get_board(board_name)
        try:
            return self.api.lists.new(name, board['id'])
        except Exception as e:
            logger.error("Error creating list: %s", e)
            raise ValueError("Error creating list")
    @backoff
    def add_card(self, name, list_id, desc=None, due=None):
        logger.info("Adding card with name: %s to list: %s", name, list_id)
        try:
            return self.api.cards.new(name, list_id, desc=desc, due=due)
        except Exception as e:
            logger.error("Error creating card: %s", e)
            raise ValueError("Error creating card")
    @backoff
    def add_checklist(self, card_id, name):
        try:
            logger.info("Adding checklist with name: %s to card: %s", name, card_id)
            return self.api.checklists.new(card_id, name)
        except Exception as e:
            logger.error("Error creating checklist: %s", e)
            raise ValueError("Error creating checklist")
    @backoff
    def add_checklist_item(self, checklist_id, name):
        try:
            logger.info("Adding checklist item with name: %s to checklist: %s", name, checklist_id)
            return self.api.checklists.new_checkItem(checklist_id, name)
        except Exception as e:
            logger.error("Error creating checklist item: %s", e)
            raise ValueError("Error creating checklist item")
    
    @backoff
    def has_label(self, card, label_name):
        try:
            return any(l['name'] == label_name for l in card['labels'])
        except KeyError:
            raise ValueError("Key 'labels' not found in card, API probably changed, data: %s" % card)
        except Exception as e:
            logger.error("Error checking label: %s", e)
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
            logger.error("Error removing label: %s", e)
            raise ValueError("Error removing label")
    
    @backoff
    def get_comments(self, card):
        """
        Returns comments from given card as list of dicts with 'text' and 'date' keys.
        """
        try:
            comments = []
            for c in self.api.cards.get(card['id'], actions='commentCard')['actions']:
                if c['type'] == 'commentCard':
                    comments.append({
                        'text': c['data']['text'],
                        'date': c['date']  # ISO 8601 format: YYYY-MM-DDTHH:MM:SS.fffZ
                    })
            return comments
        except KeyError:
            raise ValueError("Key 'comments' not found in card, API probably changed, data: %s" % card)
        except Exception as e:
            logger.error("Error getting comments: %s", e)
            raise ValueError("Error getting comments")
    
    @backoff
    def get_attachments(self, card):
        """
        Returns attachments from given card.
        """
        try:
            return self.api.cards.get(card['id'], attachments='true')['attachments']
        except KeyError:
            raise ValueError("Key 'attachments' not found in card, API probably changed, data: %s" % card)
        except Exception as e:
            logger.error("Error getting attachments: %s", e)
            raise ValueError("Error getting attachments")

    @backoff
    def attach(self, card, title, markdown_content):
        """
        Attaches HTML to given card.
        """
        logger.info("Attaching content to card %s with title %s", card["name"], title)
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
            logger.error("Error importing markdown-it-py or mdit-py-plugins")
            content = markdown_content
            try:
                with open(attachment_path, "w") as f:
                    f.write(content)
                self.api.cards.new_attachment(card['id'], open(attachment_path).read(), mimeType="text/plain", name=title + ".md")
            except Exception as e:
                logger.error("Error attaching HTML: %s", e)
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
    
    @backoff
    def get_closure_date(self, card):
        """
        Returns the closure date of the given card.
        """
        try:
            activity = self.api.cards.get(card['id'], actions='updateCard')
            f = lambda date_str: datetime.datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S.%fZ").date()
            for act in sorted(activity['actions'], key=lambda x: f(x['date']), reverse=True):
                
                if ("data" in act and 
                    'old' in act['data'] and 
                    'closed' in act['data']['old'] and
                    not act['data']['old']['closed']):
                    d = f(act['date'])
                    return d
            return None
        except Exception as e:
            raise ValueError("Error getting closure date: %s" % e)

    def get_board_name(self, card):
        """
        Returns the name of the board the given card belongs to.
        """
        try:
            board_id = card['idBoard']
            board = self.api.boards.get(board_id)
            return board['name']
        except KeyError:
            raise ValueError("Key 'idBoard' not found in card, API probably changed, data: %s" % card)
        except Exception as e:
            logger.error("Error getting board name: %s", e)
            raise ValueError("Error getting board name")
    
    def is_card_closed(self, card):
        """
        Returns True if the given card is closed, False otherwise.
        """
        try:
            return card['closed'] or card.get('dueComplete', False)
        except KeyError:
            raise ValueError("Key 'closed' not found in card, API probably changed, data: %s" % card)
        except Exception as e:
            logger.error("Error checking if card is closed: %s", e)
            raise ValueError("Error checking if card is closed")


def get_closed_dates(api: TrelloAPI, closed_cards):
    closed_this_week = {}
    for c in closed_cards:
        closure_date = api.get_closure_date(c)
        closed_this_week[c['id']] = closure_date
    return closed_this_week


def deliverables_report(api: TrelloAPI, board_name, cards, week_start):
    """
    Generates a report of deliverables for this week. Deliverables are defined as cards with 
    attachments added this week or having comments added from week start. Comments with links 
    and comments without links are included as deliverables if they are from the current week.
    Both closed and non-closed cards are considered.
    
    :param api: TrelloAPI instance
    :param board_name: Name of the board
    :param cards: List of cards to process (can be closed, open, or mixed)
    :param week_start: datetime.date object representing the start of the week
    """
    logger.info("Generating deliverables report for board %s with %d cards from week_start %s", board_name, len(cards), week_start)
    result = []
    result.append(section("Deliverables this week for board %s" % board_name))
    deliverables = {}
    
    for c in cards:
        logger.info("Processing card %s", c["name"])
        attachments = api.get_attachments(c)
        comments = api.get_comments(c)
        list_name = api.get_list_name(c)
        logger.debug(
            "Attachments: %s, Comments: %s, List name: %s",
            attachments,
            comments,
            list_name
        )
        dels = [] 
        title = c["name"]
        if list_name not in deliverables:
            deliverables[list_name] = []
        
        # Add attachments as deliverables
        for a in attachments:
            dels.append("%s: %s" % (title, a['url']))
        
        # Process comments from this week
        for com_obj in comments:
            com_text = com_obj['text']
            com_date_str = com_obj['date']
            
            # Parse comment date
            try:
                com_date = datetime.datetime.strptime(com_date_str, "%Y-%m-%dT%H:%M:%S.%fZ").date()
            except ValueError:
                logger.warning("Could not parse comment date: %s", com_date_str)
                continue
            
            # Only include comments from this week onwards
            if com_date < week_start:
                logger.debug("Skipping comment from %s (before week start %s)", com_date, week_start)
                continue
            
            # Find URLs in comment
            urls = re.findall(r'(https?://\S+)', com_text)
            
            # Include all comments from this week (with or without links)
            if len(urls) > 0:
                inline_link_re = re.compile(r'\[([^\]]+)\]\((https?://\S+)\)')
                com_text = inline_link_re.sub(r'<a href="\2">\1</a>', com_text)
                trello_inline_link_re = re.compile(r'\[([^\]]+)\]\((https?://\S+) [^\)]*\)')
                com_text = trello_inline_link_re.sub(r'<a href="\2">\1</a>', com_text)
                link_re = re.compile(r'([ \t\n])(https?://\S+)')
                com_text = link_re.sub(r'\1<a href="\2">\2</a>', com_text)
                first_link_item_re = re.compile(r'^(https?://\S+)')
                com_text = first_link_item_re.sub(r'<a href="\1">\1</a>', com_text)
            dels.append("%s: %s" % (title, com_text))
            logger.debug("Added comment from %s as deliverable", com_date)
        
        if len(dels) == 0 and api.is_card_closed(c):
            result.append(paragraph(red("Without deliverables %s - please add a comment with a link to the deliverable or attach the deliverable to the card" % ticket(c))))
        else:
            deliverables[list_name] += dels
    
    for list_name, dels in deliverables.items():
        if len(dels) == 0:
            continue
        result.append(section(list_name, level=1))
        result.append(items(dels))
    return result

def generate_report():
    logger.info("Generating Trello report")
    result = [] 
    logger.info("Loading configuration for Trello report, checking if AI help is enabled")
    ai_help_label = get_config_str("trello_ai_help_label", "Help", "Label Used in tasks in Trello to mark tasks for AI help")
    result.append("<!DOCTYPE html>")
    result.append("<html>")
    result.append("<head>")
    result.append("<meta charset='utf-8'>")
    result.append("</head>")

    result.append("<body>")
    result.append("<h1>Trello Report</h1>")
    try:
        logger.info("Initializing Trello API")
        api = TrelloAPI()
        logger.info("Trello API initialized successfully, getting backlog lists")
        backlog = api.get_lists()
        logger.debug("Backlog lists: %s", backlog)
        logger.info("Getting open cards")
        open_cards = api.get_open_cards()
        logger.info("Getting cards for this week")
        this_week = [c for c in open_cards if this_week_label in [l["name"] for l in c["labels"]]]

        card_to_list = {}
        for c in this_week:
            list_name = api.get_list_name(c)
            if list_name not in card_to_list:
                card_to_list[list_name] = []
            card_to_list[list_name].append(c)
            logger.debug("Card %s in list %s", c["name"], list_name)

        logger.debug("Cards for this week grouped by list: %s", card_to_list)
        logger.info("Generating report for cards this week with and without checklists")
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
            logger.info("Getting action points for cards in list %s without checklists, number of cards: %d", mylist, len(cards))
            apikey = load_credentials()
            for c in cards:
                result.append(paragraph(ticket(c)))
                task_description = "" 
                task_description += "Title: %s\n" % c["name"]
                task_description += "Description: %s\n" % c["desc"]
                task_description += "Project: %s\n" % mylist
                task_description += "Context: %s\n" % get_context_for_project(mylist)
                task_description += "Action points should be doable in 30 minutes each.\n"
                task_description += "Please provide a list of at most 7 action points.\n"
                logger.debug("Getting action points for card %s with description: %s", c["name"], task_description)
                suggestions = get_action_points(task_description, apikey)
                
                if len(suggestions) > 0:
                    result.append(items([s for s in suggestions]))
                    checklist = api.add_checklist(c["id"], "Checklist")
                    for s in suggestions:
                        api.add_checklist_item(checklist["id"], s)
                else:
                    result.append(paragraph("No suggestions found"))
        logger.info("Getting closed cards")
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
        days_passed = 1 + (datetime.datetime.now().date() - first_day).days
        if days_passed == 0:
            days_passed = 1
        boards = api.get_default_boards()
        logger.debug("Boards: %s", boards)
        if len(boards) == 1:
            result.append(section("Number of open cards per list"))
            data_table = [] 
            
            for l in backlog:
                data_table.append({
                    "List": l["name"],
                    "Number of open cards": len([c for c in open_cards if c["idList"] == l["id"]])
                })
            df = pd.DataFrame(data_table)
            df["Cuumulative"] = df["Number of open cards"].cumsum()
            logger.debug("Data table for open cards per list: %s", df)
            result.append(table(df))
        else:
            data_table = []
            for b in boards:
                open_cards_board = api.get_open_cards(board_name=b)
                if len(open_cards_board) == 0:
                    continue
                data_table.append({
                    "Board": b,
                    "Number of open cards": len(open_cards_board)
                })
            df = pd.DataFrame(data_table)
            result.append(section("Number of open cards per board"))
            result.append(table(df))
        logger.info("Generating statistics")
        result.append(section("Statistics"))
        result.append(paragraph("Number of open cards: %d" % len(open_cards)))
        if number_closed_cards == 0:
            result.append(paragraph("No cards closed yet. Please close some cards to see statistics."))
            return "\n".join(result)
        result.append(paragraph("Average cards closed per day: %.2f" % (number_closed_cards / days_passed)))
        start_of_week = datetime.datetime.now() - datetime.timedelta(days=datetime.datetime.now().weekday())
        start_of_week = start_of_week.date()
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
        logger.info("Calculating closed cards for this week")
        closed_dates = get_closed_dates(api, closed_cards)
        closed_this_week = [c for c in closed_cards if c['id'] in closed_dates and closed_dates[c['id']] is not None and closed_dates[c['id']] >= start_of_week]
        if get_config_bool("report_score", False, "Whether to report score for closed cards this week"):
            logger.info("Calculating score")
            score = score_closed_cards(
                api, 
                list(closed_this_week),
                closed_dates=closed_dates
            )
            result.append(paragraph("Score for this week: %d" % score))
        opened_this_week = list([c for c in open_cards if api.get_creation_date(c).date() >= start_of_week])
        result.append(paragraph("Cards opened this week: %d" % len(opened_this_week)))
        result.append("Net closure this week: %d" % (len(closed_this_week) - len(opened_this_week)))
        list_to_closed_cards = {}
        for c in closed_this_week:
            list_name = api.get_list_name(c)
            if list_name not in list_to_closed_cards:
                list_to_closed_cards[list_name] = []
            list_to_closed_cards[list_name].append(c)
        result.append(paragraph("Cards closed this week: %d" % len(closed_this_week)))
        if not get_config_bool("report_deliverables", True, "Whether to report deliverables for closed cards this week"):
            result.append(section("Closed cards this week"))
            for list_name, closed_cards in list_to_closed_cards.items():
                result.append(section(list_name, level=1))
                result.append(items([ticket(c) for c in closed_cards]))
        else:
            logger.info("Reporting deliverables for closed cards this week")
            board_to_cards = {}
            for c in closed_this_week + open_cards:
                board_name = api.get_board_name(c)
                if board_name not in board_to_cards:
                    board_to_cards[board_name] = []
                board_to_cards[board_name].append(c)
            for board_name, cards_in_board in board_to_cards.items():
                result += deliverables_report(api, board_name, cards_in_board, start_of_week)
        logger.info("Loading extensions for report")
        result += load_extensions()
        if ai_enabled:
            logger.info("AI help enabled, generating AI help for cards with label %s", ai_help_label)
            ai_help(api, open_cards, ai_help_label)
    except ValueError as e:
        result.append(error("%s" % e))
    result.append("</body>")
    result.append("</html>")
    logger.info("Report generated successfully")
    return "\n".join(result)



def ai_help(api: TrelloAPI, cards, ai_help_label):
    api_key = load_credentials()
    for card in cards:
        if api.has_label(card, ai_help_label):
            project = api.get_list_name(card)
            context = get_context_for_project(project)
            title = card["name"]
            description = card.get("desc", "")
            checklist = []
            if CheckField("idChecklists")(card):
                checklist = api.get_checklist(card)
                checklist = checklist["checkItems"]
                checklist = [c["name"] for c in checklist if c["state"] == "incomplete"]
            comment_objs = api.get_comments(card)
            # Extract just the text from comment objects for compatibility with get_help_with_task
            comments = [c['text'] for c in comment_objs] if comment_objs else None

            attachment_name = f"{project} - {title}"
            api.remove_label(card, ai_help_label)
            logger.info("Removed label %s from card %s", ai_help_label, attachment_name)
            if context is not None and context != "":
                description = "%s\n\nContext:\n%s" % (description, context)
            response = get_help_with_task(api_key, project, title, description, checklist or None, comments or None)
            api.attach(card, attachment_name, response)
            logger.info("Attached response to card %s", attachment_name)

class TrelloImporter(Importer):

    def __init__(self):
        self.api = TrelloAPI()

    def list_projects(self, board_name=None):
        return [l["name"].strip() for l in self.api.get_lists(board_name=board_name)]

    def create(self, title, description, due_date = None, context = None, project = None, checklists = None):
        # context here represents the board
        board_name = None 
        boards = self.api.get_default_boards()
        if context is None:
            board_name = boards[0]
            context = board_name
        if context not in boards:
            raise ValueError("Board %s not found in Trello boards: %s" % (context, ", ".join(boards)))
        logger.info("""
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
            project = self.list_projects(context)[0]
        else:
            project = project.strip()
        if project not in self.list_projects(context):
            logger.info("Project %s not found, creating it", project)
            self.api.add_list(project, board_name=context)
        list_id = next(l for l in self.api.get_lists(context) if l["name"].strip() == project)["id"]
        card = self.api.add_card(title, list_id, desc=description, due=due_date)
        if checklists is not None and len(checklists.keys()) > 0:
            for checklist_name, checklist_items in checklists.items():
                if len(checklist_items) > 0:
                    checklist_id = self.api.add_checklist(card["id"], checklist_name)["id"]
                    for item in checklist_items:
                        self.api.add_checklist_item(checklist_id, item)
        logger.info("Card created: %s", card["shortUrl"])
        return card["shortUrl"]

    def create_project(self, name, context = None):
        self.api.add_list(name, board_name=context)
    
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
            project = self.list_projects(context)[0]
        list_id = next(iter([l for l in self.api.get_lists(context) if l["name"] == project]), {"id": None})["id"]
        if list_id is None:
            return False 
        cards = self.api.get_open_cards(context)
        for card in cards:
            if card["name"] == title and card["idList"] == list_id:
                return True
        return False    

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
            result.append(section("%s (%d card%s)" % (
                mylist,
                len(cards),
                "s" if len(cards) > 1 else ""
            ), level=1))
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
        logger.info("Generating report of open cards in Trello")
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
        logger.info("Generating report of closed cards in Trello")
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
        logger.info("Generating report of cards for this week in Trello")
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
        logger.info("Generating report of net closure of cards this week in Trello")
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

primary_label = get_config_str("trello_primary_label", "Primary", "Label used in Trello to mark primary tasks")
secondary_label = get_config_str("trello_secondary_label", "Secondary", "Label used in Trello to mark secondary tasks")

def score_closed_cards(
        api: TrelloAPI, 
        closed_cards=None, 
        closed_dates=None,
        score_from_date=None,
        score_to_date=None
    ) -> int:
    """
    Scores closed cards on a Trello board. 

    Based on label and the fact if the card closed the list, score is calculated as follows:

    - If the card has a "Primary" label and is closed, it scores 3 points.
    - If the card has a "Secondary" label and is closed, it scores 1 point.
    - If the card is closed but does not have either label, it scores 1 point.
    - If the card closed the list, it scores 4 points.

    Args:
        api (TrelloAPI): An instance of the TrelloAPI class to interact with the Trello API.
        closed_cards (list): A list of closed cards to be scored.
        closed_dates (dict): A dictionary mapping card IDs to their closed dates.
        score_from_date (datetime): If provided, only cards closed on or after this date will be scored.
        score_to_date (datetime): If provided, only cards closed on or before this date will be scored.
    Returns:
        int: The total score of closed cards on the board.
    """
    logger.info(f"Scoring {len(closed_cards)} closed cards.")
    if closed_cards is None:
        closed_cards = api.get_closed_cards()
    if closed_dates is None:
        closed_dates = {
            card['id']: card.get("dateLastActivity", datetime.datetime.min) for card in closed_cards
        }
    total_score = 0
    already_closed_list_ids = set()
    closed_lists = api.get_closed_lists()
    list_closure_cards = {}
    for closed_list in closed_lists:
        logger.debug(f"Processing closed list '{closed_list.get('name')}' (ID: {closed_list.get('id')})")
        list_cards = [
            card for card in closed_cards 
            if card.get('idList') == closed_list['id']
        ]
        if list_cards:
            list_closure_cards[closed_list['id']] = max(
                list_cards,
                key=lambda c: closed_dates.get(c['id'], datetime.datetime.min)
            )
        else:
            logger.debug(f"No closed cards found for list '{closed_list.get('name')}' (ID: {closed_list.get('id')})")
    for card in closed_cards:
        if score_from_date or score_to_date:
            closed_date = closed_dates.get(card['id'])
            if closed_date is None:
                logger.warning(f"Card '{card.get('name')}' does not have a closed date. Skipping scoring.")
                continue
            if score_from_date and closed_date <= score_from_date:
                logger.debug(f"Card '{card.get('name')}' closed on {closed_date}, which is before the score_from_date {score_from_date}. Skipping scoring.")
                continue
            if score_to_date and closed_date >= score_to_date:
                logger.debug(f"Card '{card.get('name')}' closed on {closed_date}, which is after the score_to_date {score_to_date}. Skipping scoring.")
                continue
        card_score = 0
        if api.has_label(card, primary_label):
            card_score = 3
        elif api.has_label(card, secondary_label):
            card_score = 1
        else:
            card_score = 1

        list_id = card.get('idList')
        if list_id and list_id not in already_closed_list_ids:
            if any(closed_list['id'] == list_id for closed_list in closed_lists):
                # If the card closed the list, it scores 4 points.
                if list_closure_cards.get(list_id, {}).get("id", "") == card['id']:
                    card_score = 4
                already_closed_list_ids.add(list_id)
        logger.debug(f"Card '{card.get('name')}' scored {card_score} points.")
        total_score += card_score
    return total_score

