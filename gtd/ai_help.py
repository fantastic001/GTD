import logging
from typing import List

from gtd.context_keys import ContextKey
from gtd.extraction import ExtractionError
from gtd.extraction.runner import run_extraction

logger = logging.getLogger(__name__)


def request_ai_help() -> List[str]:
    try:
        context = run_extraction([ContextKey.AI_HELP_REQUESTS])
    except ExtractionError as e:
        logger.error("AI help extraction failed: %s", e)
        raise
    requested = list(context[ContextKey.AI_HELP_REQUESTS])
    logger.info("AI help requested for %s", requested)
    return requested
