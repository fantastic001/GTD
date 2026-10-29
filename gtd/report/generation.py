import logging
from typing import List

from gtd.context_keys import ContextKey
from gtd.extraction import ExtractionError
from gtd.extraction.runner import run_extraction
from gtd.style import error

logger = logging.getLogger(__name__)


def generate_report_elements() -> List[str]:
    try:
        context = run_extraction([ContextKey.REPORT])
    except ExtractionError as e:
        logger.error("Report extraction failed: %s", e)
        return [error(str(e))]
    return list(context[ContextKey.REPORT])
