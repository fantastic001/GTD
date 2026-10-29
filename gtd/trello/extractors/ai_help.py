import logging
from typing import Callable, List

from gtd.context_keys import ContextKey
from gtd.extraction.extractor import Context, Extractor
from gtd.trello.context_keys import TrelloContextKey

logger = logging.getLogger(__name__)

AiHelpRequester = Callable[[object, list, str], None]


class TrelloAiHelpExtractor(Extractor):

    def __init__(
        self,
        api,
        ai_help_label: str,
        request_ai_help: AiHelpRequester
    ) -> None:
        self._api = api
        self._ai_help_label = ai_help_label
        self._request_ai_help = request_ai_help

    def dependencies(self) -> List[str]:
        return [TrelloContextKey.OPEN_CARDS]

    def output(self) -> List[str]:
        return [ContextKey.AI_HELP_REQUESTS]

    def extract(self, context: Context) -> Context:
        cards = context[TrelloContextKey.OPEN_CARDS]
        requested = [
            card["name"] for card in cards
            if self._api.has_label(card, self._ai_help_label)
        ]
        logger.info("Requesting AI help for cards %s", requested)
        self._request_ai_help(self._api, cards, self._ai_help_label)
        return {ContextKey.AI_HELP_REQUESTS: requested}
