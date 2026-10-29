from typing import List, Sequence

from gtd.extraction.extractor import Context, Extractor
from gtd.trello.context_keys import TrelloContextKey


class TrelloClosedListExtractor(Extractor):

    def __init__(self, api, board_names: Sequence[str]) -> None:
        self._api = api
        self._board_names = list(board_names)

    def dependencies(self) -> List[str]:
        return []

    def output(self) -> List[str]:
        return [TrelloContextKey.CLOSED_LISTS]

    def extract(self, context: Context) -> Context:
        return {
            TrelloContextKey.CLOSED_LISTS: [
                lst
                for board_name in self._board_names
                for lst in self._api.get_closed_lists(board_name=board_name)
            ]
        }
