from typing import List

from gtd.extraction.extractor import Context, Extractor
from gtd.trello import get_closed_dates
from gtd.trello.context_keys import TrelloContextKey


class TrelloClosureDatesExtractor(Extractor):

    def __init__(self, api) -> None:
        self._api = api

    def dependencies(self) -> List[str]:
        return [TrelloContextKey.CLOSED_CARDS]

    def output(self) -> List[str]:
        return [TrelloContextKey.CLOSURE_DATES]

    def extract(self, context: Context) -> Context:
        return {
            TrelloContextKey.CLOSURE_DATES: get_closed_dates(
                self._api,
                context[TrelloContextKey.CLOSED_CARDS]
            )
        }
