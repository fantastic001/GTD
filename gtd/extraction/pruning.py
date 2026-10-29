import logging
from typing import Dict, List, Sequence, Set

from gtd.extraction.extractor import Extractor

logger = logging.getLogger(__name__)


def index_producers_by_key(
    extractors: Sequence[Extractor]
) -> Dict[str, List[int]]:
    producers: Dict[str, List[int]] = {}
    for index, extractor in enumerate(extractors):
        for key in extractor.output():
            producers.setdefault(key, []).append(index)
    return producers


def collect_needed_indices(
    extractors: Sequence[Extractor],
    required_keys: Sequence[str]
) -> Set[int]:
    producers = index_producers_by_key(extractors)
    needed: Set[int] = set()
    pending_keys = list(required_keys)
    visited_keys: Set[str] = set()
    while pending_keys:
        key = pending_keys.pop()
        if key in visited_keys:
            continue
        else:
            visited_keys.add(key)
        for index in producers.get(key, []):
            needed.add(index)
            pending_keys.extend(extractors[index].dependencies())
    return needed


def select_extractors_needed_for(
    extractors: Sequence[Extractor],
    required_keys: Sequence[str]
) -> List[Extractor]:
    needed = collect_needed_indices(extractors, required_keys)
    selected = [e for i, e in enumerate(extractors) if i in needed]
    logger.info(
        "Extractors needed for %s: %s; skipped: %s",
        list(required_keys),
        [extractor.name() for extractor in selected],
        [e.name() for i, e in enumerate(extractors) if i not in needed]
    )
    return selected
