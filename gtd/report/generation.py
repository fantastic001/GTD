import datetime
import logging
from typing import Any, List, Mapping

from gtd.context_keys import ContextKey
from gtd.extraction import ExtractionError
from gtd.extraction.runner import run_extraction
from gtd.style import error

logger = logging.getLogger(__name__)


def generate_elements_of(
    report_key: str,
    initial_context: Mapping[str, Any]
) -> List[str]:
    try:
        context = run_extraction([report_key], initial_context)
    except ExtractionError as e:
        logger.error("Extraction of %s failed: %s", report_key, e)
        return [error(str(e))]
    return list(context[report_key])


def generate_report_elements() -> List[str]:
    return generate_elements_of(ContextKey.REPORT, {})


def generate_monthly_report_elements(month: datetime.date) -> List[str]:
    logger.info("Generating monthly report for %s", month)
    return generate_elements_of(
        ContextKey.MONTHLY_REPORT,
        {ContextKey.REPORT_MONTH: month}
    )
