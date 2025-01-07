
from gtd.trello import TrelloAPI
import sys 
import json


api = TrelloAPI()

if sys.argv[1] == "backup":
    cards = api.get_open_cards("Backlog")
    closed_cards = api.get_closed_cards("Backlog")
    backup_file = sys.argv[2]
    with open(backup_file, "w") as f:
        json.dump({
            "open_cards": cards,
            "closed_cards": closed_cards
        }, f)

