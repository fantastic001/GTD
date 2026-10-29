import logging
from typing import Any, List

from gtd.extraction.errors import ExtractionError
from gtd.extraction.introspection import describe_producers
from gtd.extraction.runner import load_all_extractors, run_extraction
from gtd.extraction.serialization import (
    ensure_format_is_supported,
    format_value,
)

logger = logging.getLogger(__name__)


def ensure_key_is_named(key: str) -> None:
    if not key or not key.strip():
        raise ValueError("Context key must not be empty")
    else:
        logger.debug("Context key %s requested", key)


def describe_key_producers(key: str) -> List[str]:
    ensure_key_is_named(key)
    try:
        producers = describe_producers(load_all_extractors(), key)
    except ExtractionError as e:
        logger.error("Describing producers of %s failed: %s", key, e)
        raise
    return [str(producer) for producer in producers]


def extract_key(key: str, output_format: str) -> Any:
    ensure_key_is_named(key)
    ensure_format_is_supported(output_format)
    try:
        context = run_extraction([key])
    except ExtractionError as e:
        logger.error("Extraction of %s failed: %s", key, e)
        raise
    return format_value(context[key], output_format)
