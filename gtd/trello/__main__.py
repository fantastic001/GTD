
import trello 
import os
import json  
import datetime 

current_utc_time = datetime.datetime.utcnow()
current_time = datetime.datetime.now()
dt = current_time - current_utc_time

def utc_to_this_tz(utc_time):
    return datetime.datetime.strptime(utc_time, "%Y-%m-%dT%H:%M:%S.%fZ") + dt

apikey = json.loads(open('apikey.json').read())["key"]
api = trello.TrelloApi(apikey=apikey)

api.set_token(json.loads(open('apikey.json').read())["token"])


boards = api.members.get_board('me')

backlog_board = next(b for b in boards if b['name'] == 'Backlog')

lists = api.boards.get_list(backlog_board['id'])

archived_cards = api.boards.get_card(backlog_board['id'], filter='closed')
print("Archived cards")
for c in archived_cards:
    print(c['name'])
    print("   Archived on " + utc_to_this_tz(c['dateLastActivity']).strftime("%Y-%m-%d %H:%M:%S"))
    print("   List: " + next(l['name'] for l in lists if l['id'] == c['idList']))

# for l in lists:
#     print(l['name'])
#     cards = api.lists.get_card(l['id'])
#     for c in cards:
#         print(f"  {c['name']}")
#     archived_cards = [c for c in cards if c['closed']]
#     for c in archived_cards:
#         print(f"  {c['name']}")