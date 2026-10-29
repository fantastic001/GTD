from typing import List

from gtd.context_keys import ContextKey
from gtd.extraction.extractor import Context, Extractor
from gtd.trello.context_keys import TrelloContextKey
from gtd.trello.task_mapping import TrelloCardToTaskMapper


class TrelloOpenTasksExtractor(Extractor):

    def __init__(self, api, this_week_label: str) -> None:
        self._api = api
        self._this_week_label = this_week_label

    def dependencies(self) -> List[str]:
        return [
            TrelloContextKey.BOARDS,
            TrelloContextKey.LISTS,
            TrelloContextKey.OPEN_CARDS,
        ]

    def output(self) -> List[str]:
        return [ContextKey.OPEN_TASKS]

    def extract(self, context: Context) -> Context:
        mapper = TrelloCardToTaskMapper(
            self._api,
            context[TrelloContextKey.BOARDS],
            context[TrelloContextKey.LISTS],
            self._this_week_label
        )
        return {
            ContextKey.OPEN_TASKS: [
                mapper.map_card(card, {})
                for card in context[TrelloContextKey.OPEN_CARDS]
            ]
        }
