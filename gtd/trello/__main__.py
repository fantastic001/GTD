
from gtd.config import get_config_str
from gtd.trello import TrelloAPI, ai_help
import sys 
import json


api = TrelloAPI()

if sys.argv[1] == "backup":
    backlog = api.get_default_boards()
    cards = api.get_open_cards(backlog)
    closed_cards = api.get_closed_cards(backlog)
    backup_file = sys.argv[2]
    with open(backup_file, "w") as f:
        json.dump({
            "open_cards": [
                {
                    "checklist": api.get_checklist(card),
                    **card,
                } for card in cards
            ],
            "closed_cards": closed_cards
        }, f)
elif sys.argv[1] == "list":
    for board in api.get_boards():
        print(f"{board['name']} ({board['id']})")
elif sys.argv[1] == "ai":
    this_week_label = "This week"
    cards = [c for c in api.get_open_cards() if this_week_label in [l["name"] for l in c["labels"]]]
    ai_help(api, cards, "Help")
elif sys.argv[1] == "comments":
    this_week_label = "This week"
    cards = [c for c in api.get_open_cards() if this_week_label in [l["name"] for l in c["labels"]]]
    for card in cards:
        if api.has_label(card, "Help"):
            for c in api.get_comments(card):
                print(c)