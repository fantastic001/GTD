
import trello 
import os
import json  
import datetime 
from gtd.config import get_config_str
from gtd.style import *


def utc_to_this_tz(utc_time):
    current_utc_time = datetime.datetime.utcnow()
    current_time = datetime.datetime.now()
    dt = current_time - current_utc_time
    return datetime.datetime.strptime(utc_time, "%Y-%m-%dT%H:%M:%S.%fZ") + dt

class TrelloAPI:
    def __init__(self, apikey=None, token=None) -> None:
        
        if apikey is None:
            apikey = get_config_str("trello_apikey", "", "Trello API key")
        api = trello.TrelloApi(apikey=apikey)
        if token is None:
            token = get_config_str("trello_token", "", "Trello token")
        api.set_token(token)
        self.api = api

    def get_boards(self):
        return self.api.members.get_board('me')

    def get_board(self, board_name):
        return next(b for b in self.get_boards() if b['name'] == board_name)

    def get_lists(self, board_name):
        board = self.get_board(board_name)
        return self.api.boards.get_list(board['id'])

    def get_open_cards(self, board_name):
        board = self.get_board(board_name)
        return self.api.boards.get_card(board['id'])

    def get_closed_cards(self, board_name):
        board = self.get_board(board_name)
        return self.api.boards.get_card(board['id'], filter='closed')

    def get_closed_lists(self, board_name):
        board = self.get_board(board_name)
        return self.api.boards.get_list(board['id'], filter='closed')

def generate_report():
    result = [] 
    result.append("<!DOCTYPE html>")
    result.append("<html>")
    result.append("<head>")
    result.append("<meta charset='utf-8'>")
    result.append("</head>")

    result.append("<body>")
    result.append("<h1>Trello Report</h1>")

    api = TrelloAPI()
    backlog = api.get_lists("Backlog")

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
    result.append(paragraph("Last card closed on %s" % api.get_closed_cards("Backlog")[0]["dateLastActivity"]))
    result.append(paragraph("Cards closed this week: %d" % len(closed_this_week)))
    result.append(section("Closed cards this week"))
    result.append(items([ticket(c) for c in closed_this_week]))
    result.append("</body>")
    result.append("</html>")
    return "\n".join(result)