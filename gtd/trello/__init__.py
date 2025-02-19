
import trello 
import os
import json  
import datetime 
from gtd.config import get_config_str
from gtd.style import *


def utc_to_this_tz(utc_time: str) -> datetime.datetime | None:
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

    def get_boards(self):
        try:
            return self.api.members.get_board('me')
        except Exception as e:
            print("Error getting boards: %s" % e)
            raise ValueError("Error getting boards")

    def get_board(self, board_name):
        try:
            return next(b for b in self.get_boards() if b['name'] == board_name)
        except StopIteration:
            raise ValueError("Board not found: %s" % board_name)
        except KeyError:
            raise ValueError("Key 'name' not found in board, API probably changed")

    def get_lists(self, board_name):
        board = self.get_board(board_name)
        try:
            return self.api.boards.get_list(board['id'])
        except Exception as e:
            print("Error getting lists: %s" % e)
            raise ValueError("Error getting lists")

    def get_open_cards(self, board_name):
        board = self.get_board(board_name)
        try:
            return list(filter(NotCheckField("dueComplete"), self.api.boards.get_card(board['id'])))
        except Exception as e:
            print("Error getting cards: %s" % e)
            raise ValueError("Error getting cards")

    def get_closed_cards(self, board_name):
        board = self.get_board(board_name)
        try:
            return self.api.boards.get_card(board['id'], filter='closed') + list(filter(CheckField("dueComplete"), self.api.boards.get_card(board['id'])))
        except Exception as e:
            print("Error getting cards: %s" % e)
            raise ValueError("Error getting cards")

    def get_closed_lists(self, board_name):
        board = self.get_board(board_name)
        try:
            return self.api.boards.get_list(board['id'], filter='closed')
        except Exception as e:
            print("Error getting lists: %s" % e)
            raise ValueError("Error getting lists")
    
    def get_list_name(self, card):
        try:
            return self.api.lists.get(card['idList'])['name']
        except KeyError:
            raise ValueError("Key 'name' not found in list, API probably changed, data: %s" % card)
        except Exception as e:
            print("Error getting list name: %s" % e)
            raise ValueError("Error getting list name")

def generate_report():
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
        backlog = api.get_lists("Backlog")
        open_cards = api.get_open_cards("Backlog")

        result.append(section("Tickets this week"))
        result.append(items([ticket(c) for c in api.get_open_cards("Backlog") if "This week" in [l["name"] for l in c["labels"]]]))
        
        number_closed_cards = len(api.get_closed_cards("Backlog"))
        days_passed = 1 + (datetime.datetime.now().date() - datetime.date(2025,1,5)).days
        result.append(section("Statistics"))
        result.append(paragraph("Average cards closed per day: %.2f" % (number_closed_cards / days_passed)))
        start_of_week = datetime.datetime.now() - datetime.timedelta(days=datetime.datetime.now().weekday())
        start_of_week = start_of_week.date()
        result.append(paragraph("Number of open cards: %d" % len(api.get_open_cards("Backlog"))))
        result.append(paragraph("Start of week: %s" % start_of_week))
        closed_this_week = list([c for c in api.get_closed_cards("Backlog") if datetime.datetime.strptime(c["dateLastActivity"], "%Y-%m-%dT%H:%M:%S.%fZ").date() >= start_of_week])
        list_to_closed_cards = {}
        for c in closed_this_week:
            list_name = api.get_list_name(c)
            if list_name not in list_to_closed_cards:
                list_to_closed_cards[list_name] = []
            list_to_closed_cards[list_name].append(c)
        if len(closed_this_week) > 0:
            result.append(paragraph("Last card closed on %s" % api.get_closed_cards("Backlog")[0]["dateLastActivity"]))
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
    except ValueError as e:
        result.append(paragraph("Error: %s" % e))
    result.append("</body>")
    result.append("</html>")
    return "\n".join(result)