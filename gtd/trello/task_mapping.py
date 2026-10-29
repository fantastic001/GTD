import datetime
from typing import Any, Dict, Mapping, Optional, Sequence

from gtd.domain import Task
from gtd.trello import CheckField, utc_to_this_tz

TRELLO_SOURCE = "trello"
TRELLO_DATE_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"

Card = Dict[str, Any]


def parse_trello_date(value: Optional[str]) -> Optional[datetime.date]:
    if value:
        return datetime.datetime.strptime(value, TRELLO_DATE_FORMAT).date()
    else:
        return None


def parse_trello_due(value: Optional[str]) -> Optional[datetime.datetime]:
    if value:
        return utc_to_this_tz(value)
    else:
        return None


class TrelloCardToTaskMapper:

    def __init__(
        self,
        api,
        boards: Sequence[Card],
        lists: Sequence[Card],
        this_week_label: str
    ) -> None:
        self._api = api
        self._board_names = {board["id"]: board["name"] for board in boards}
        self._list_names = {lst["id"]: lst["name"].strip() for lst in lists}
        self._this_week_label = this_week_label

    def map_card(
        self,
        card: Card,
        closure_dates: Mapping[str, Optional[datetime.date]]
    ) -> Task:
        labels = tuple(label["name"] for label in card.get("labels", []))
        return Task(
            source=TRELLO_SOURCE,
            identifier=card["id"],
            title=card["name"],
            description=card.get("desc", ""),
            url=card["shortUrl"],
            reference=card["shortLink"],
            project=self._resolve_list_name(card),
            context=self._resolve_board_name(card),
            labels=labels,
            due=parse_trello_due(card.get("due")),
            created=self._api.get_creation_date(card),
            last_activity=parse_trello_date(card.get("dateLastActivity")),
            closed_on=closure_dates.get(card["id"]),
            is_closed=bool(self._api.is_card_closed(card)),
            is_planned_this_week=self._this_week_label in labels,
            has_checklist=bool(CheckField("idChecklists")(card)),
        )

    def _resolve_list_name(self, card: Card) -> str:
        if card["idList"] in self._list_names:
            return self._list_names[card["idList"]]
        else:
            return self._api.get_list_name(card).strip()

    def _resolve_board_name(self, card: Card) -> str:
        if card["idBoard"] in self._board_names:
            return self._board_names[card["idBoard"]]
        else:
            return self._api.get_board_name(card)
