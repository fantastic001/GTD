from typing import List, Sequence

from gtd.extraction.extractor import Context, Extractor
from gtd.trello.context_keys import TrelloContextKey


class TrelloClosedCardsExtractor(Extractor):

    def __init__(self, api, board_names: Sequence[str]) -> None:
        self._api = api
        self._board_names = list(board_names)

    def dependencies(self) -> List[str]:
        return []

    def output(self) -> List[str]:
        return [TrelloContextKey.CLOSED_CARDS]

    def extract(self, context: Context) -> Context:
        return {
            TrelloContextKey.CLOSED_CARDS: [
                card
                for board_name in self._board_names
                for card in self._api.get_closed_cards(board_name=board_name)
            ]
        }
