from dataclasses import dataclass
from typing import List, Sequence, Tuple

from gtd.extraction.errors import MissingDependencyError
from gtd.extraction.extractor import Extractor


@dataclass(frozen=True)
class ProducerDescription:
    extractor: str
    dependencies: Tuple[str, ...]

    def __str__(self) -> str:
        if self.dependencies:
            return "%s <- %s" % (self.extractor, ", ".join(self.dependencies))
        else:
            return "%s <- (no dependencies)" % self.extractor


def describe_producers(
    extractors: Sequence[Extractor],
    key: str
) -> List[ProducerDescription]:
    descriptions = [
        ProducerDescription(
            extractor.name(),
            tuple(extractor.dependencies())
        )
        for extractor in extractors
        if key in extractor.output()
    ]
    if descriptions:
        return descriptions
    else:
        raise MissingDependencyError("No extractor provides key '%s'" % key)
