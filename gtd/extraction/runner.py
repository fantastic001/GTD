import logging
from typing import List, Sequence

from gtd.config import get_config_int
from gtd.extraction.extractor import Context, Extractor
from gtd.extraction.loader import create_extractors, load_extractor_factories
from gtd.extraction.pipeline import ExtractionPipeline

logger = logging.getLogger(__name__)

DEFAULT_EXTRACTION_WORKERS = 8


def load_all_extractors() -> List[Extractor]:
    return create_extractors(load_extractor_factories())


def run_extraction(required_keys: Sequence[str]) -> Context:
    if not required_keys:
        raise ValueError("At least one required key must be requested")
    max_workers = get_config_int(
        "extraction_max_workers",
        DEFAULT_EXTRACTION_WORKERS,
        "Number of extractors allowed to run concurrently"
    )
    extractors = load_all_extractors()
    logger.info("Running extraction for keys %s", list(required_keys))
    return ExtractionPipeline(extractors, max_workers).run(
        {},
        required_keys=required_keys
    )
