from typing import List

from gtd.context_keys import ContextKey
from gtd.extraction.extractor import Context, Extractor
from gtd.trello.context_keys import TrelloContextKey
from gtd.trello.task_mapping import TrelloCardToTaskMapper


class TrelloClosedTasksExtractor(Extractor):

    def __init__(self, api, this_week_label: str) -> None:
        self._api = api
        self._this_week_label = this_week_label

    def dependencies(self) -> List[str]:
        return [
            TrelloContextKey.BOARDS,
            TrelloContextKey.LISTS,
            TrelloContextKey.CLOSED_LISTS,
            TrelloContextKey.CLOSED_CARDS,
            TrelloContextKey.CLOSURE_DATES,
        ]

    def output(self) -> List[str]:
        return [ContextKey.CLOSED_TASKS]

    def extract(self, context: Context) -> Context:
        mapper = TrelloCardToTaskMapper(
            self._api,
            context[TrelloContextKey.BOARDS],
            context[TrelloContextKey.LISTS]
            + context[TrelloContextKey.CLOSED_LISTS],
            self._this_week_label
        )
        closure_dates = context[TrelloContextKey.CLOSURE_DATES]
        return {
            ContextKey.CLOSED_TASKS: [
                mapper.map_card(card, closure_dates)
                for card in context[TrelloContextKey.CLOSED_CARDS]
            ]
        }
