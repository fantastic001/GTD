from typing import List

from gtd.context_keys import ContextKey
from gtd.extraction.extractor import Context, Extractor
from gtd.trello import score_closed_cards
from gtd.trello.context_keys import TrelloContextKey


class TrelloScoreExtractor(Extractor):

    def __init__(self, api) -> None:
        self._api = api

    def dependencies(self) -> List[str]:
        return [
            TrelloContextKey.CLOSED_CARDS,
            TrelloContextKey.CLOSURE_DATES,
            ContextKey.WEEK_START,
        ]

    def output(self) -> List[str]:
        return [ContextKey.WEEKLY_SCORE]

    def extract(self, context: Context) -> Context:
        closure_dates = context[TrelloContextKey.CLOSURE_DATES]
        week_start = context[ContextKey.WEEK_START]
        closed_this_week = [
            card for card in context[TrelloContextKey.CLOSED_CARDS]
            if closure_dates.get(card["id"]) is not None
            and closure_dates[card["id"]] >= week_start
        ]
        return {
            ContextKey.WEEKLY_SCORE: score_closed_cards(
                self._api,
                closed_this_week,
                closed_dates=closure_dates
            )
        }
