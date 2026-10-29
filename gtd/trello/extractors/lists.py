from typing import List, Sequence

from gtd.context_keys import ContextKey
from gtd.domain import Project
from gtd.extraction.extractor import Context, Extractor
from gtd.trello.context_keys import TrelloContextKey


class TrelloListExtractor(Extractor):

    def __init__(self, api, board_names: Sequence[str]) -> None:
        self._api = api
        self._board_names = list(board_names)

    def dependencies(self) -> List[str]:
        return []

    def output(self) -> List[str]:
        return [TrelloContextKey.LISTS, ContextKey.PROJECTS]

    def extract(self, context: Context) -> Context:
        lists_per_board = [
            (board_name, self._api.get_lists(board_name=board_name))
            for board_name in self._board_names
        ]
        return {
            TrelloContextKey.LISTS: [
                lst for _, lists in lists_per_board for lst in lists
            ],
            ContextKey.PROJECTS: [
                Project(name=lst["name"].strip(), context=board_name)
                for board_name, lists in lists_per_board
                for lst in lists
            ],
        }
