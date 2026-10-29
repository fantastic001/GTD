from graphlib import CycleError, TopologicalSorter
from typing import Dict, Iterable, List, Sequence, Set

from gtd.extraction.errors import (
    ConflictingOutputError,
    CyclicDependencyError,
    ExtractorContractError,
    MissingDependencyError,
)
from gtd.extraction.extractor import Extractor


class ExtractionGraph:

    def __init__(
        self,
        extractors: Sequence[Extractor],
        available_keys: Iterable[str],
        required_keys: Iterable[str] = ()
    ) -> None:
        self._extractors = list(extractors)
        self._available_keys = frozenset(available_keys)
        self._producers = self._index_producers_by_key()
        self._ensure_dependencies_are_provided()
        self._ensure_required_keys_are_provided(list(required_keys))

    def extractor(self, index: int) -> Extractor:
        return self._extractors[index]

    def producer_count(self, key: str) -> int:
        return len(self._producers.get(key, []))

    def create_sorter(self) -> TopologicalSorter:
        sorter = TopologicalSorter({
            index: self._predecessors(index)
            for index in range(len(self._extractors))
        })
        try:
            sorter.prepare()
        except CycleError as e:
            cycle = [self._extractors[index].name() for index in e.args[1]]
            raise CyclicDependencyError(
                "Extractors depend on each other in a cycle: %s"
                % " -> ".join(cycle)
            ) from e
        return sorter

    def _index_producers_by_key(self) -> Dict[str, List[int]]:
        producers: Dict[str, List[int]] = {}
        for index, extractor in enumerate(self._extractors):
            for key in self._validated_output(extractor):
                producers.setdefault(key, []).append(index)
        return producers

    def _validated_output(self, extractor: Extractor) -> List[str]:
        output = list(extractor.output())
        if len(set(output)) != len(output):
            raise ExtractorContractError(
                "Extractor %s lists duplicate output keys: %s"
                % (extractor.name(), output)
            )
        already_available = self._available_keys.intersection(output)
        if already_available:
            raise ConflictingOutputError(
                "Extractor %s outputs keys already present in context: %s"
                % (extractor.name(), sorted(already_available))
            )
        else:
            return output

    def _is_provided(self, key: str) -> bool:
        return key in self._available_keys or key in self._producers

    def _ensure_dependencies_are_provided(self) -> None:
        missing = [
            "%s requires '%s'" % (extractor.name(), key)
            for extractor in self._extractors
            for key in extractor.dependencies()
            if not self._is_provided(key)
        ]
        if missing:
            raise MissingDependencyError(
                "No extractor provides required keys: %s" % "; ".join(missing)
            )

    def _ensure_required_keys_are_provided(
        self,
        required_keys: List[str]
    ) -> None:
        missing = [key for key in required_keys if not self._is_provided(key)]
        if missing:
            raise MissingDependencyError(
                "No extractor provides requested keys: %s" % missing
            )

    def _predecessors(self, index: int) -> Set[int]:
        return {
            producer
            for key in self._extractors[index].dependencies()
            for producer in self._producers.get(key, [])
        }
