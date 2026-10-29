from typing import List, Sequence

from gtd.extraction.extractor import Context, Extractor
from gtd.trello.context_keys import TrelloContextKey


class TrelloOpenCardsExtractor(Extractor):

    def __init__(self, api, board_names: Sequence[str]) -> None:
        self._api = api
        self._board_names = list(board_names)

    def dependencies(self) -> List[str]:
        return []

    def output(self) -> List[str]:
        return [TrelloContextKey.OPEN_CARDS]

    def extract(self, context: Context) -> Context:
        return {
            TrelloContextKey.OPEN_CARDS: [
                card
                for board_name in self._board_names
                for card in self._api.get_open_cards(board_name=board_name)
            ]
        }
