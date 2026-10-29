from typing import List, Sequence

from gtd.context_keys import ContextKey
from gtd.extraction.extractor import Context, Extractor
from gtd.trello.context_keys import TrelloContextKey


class TrelloBoardsExtractor(Extractor):

    def __init__(self, api, board_names: Sequence[str]) -> None:
        self._api = api
        self._board_names = list(board_names)

    def dependencies(self) -> List[str]:
        return []

    def output(self) -> List[str]:
        return [TrelloContextKey.BOARDS, ContextKey.CONTEXTS]

    def extract(self, context: Context) -> Context:
        boards = [self._api.get_board(name) for name in self._board_names]
        return {
            TrelloContextKey.BOARDS: boards,
            ContextKey.CONTEXTS: [board["name"] for board in boards],
        }
