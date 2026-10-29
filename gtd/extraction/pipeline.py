import logging
from concurrent.futures import (
    FIRST_COMPLETED,
    Executor,
    Future,
    ThreadPoolExecutor,
    wait,
)
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence

from gtd.extraction.errors import (
    ExtractionError,
    ExtractorContractError,
    ExtractorFailedError,
)
from gtd.extraction.extractor import Context, Extractor
from gtd.extraction.graph import ExtractionGraph
from gtd.extraction.merge import ContextValueMerger
from gtd.extraction.pruning import select_extractors_needed_for

logger = logging.getLogger(__name__)


def run_extractor(extractor: Extractor, context: Context) -> Context:
    logger.info(
        "Running extractor %s with dependencies %s",
        extractor.name(),
        list(context.keys())
    )
    try:
        result = extractor.extract(context)
    except Exception as e:
        logger.error("Extractor %s failed: %s", extractor.name(), e)
        raise ExtractorFailedError(
            "Extractor %s failed: %s" % (extractor.name(), e)
        ) from e
    ensure_result_matches_output(extractor, result)
    logger.info(
        "Extractor %s produced keys %s",
        extractor.name(),
        list(result.keys())
    )
    return dict(result)


def ensure_result_matches_output(extractor: Extractor, result: Any) -> None:
    if not isinstance(result, Mapping):
        raise ExtractorContractError(
            "Extractor %s returned %s instead of a mapping"
            % (extractor.name(), type(result).__name__)
        )
    elif set(result.keys()) != set(extractor.output()):
        raise ExtractorContractError(
            "Extractor %s returned keys %s but declares output %s"
            % (extractor.name(), sorted(result.keys()), extractor.output())
        )
    else:
        logger.debug("Extractor %s honoured its output", extractor.name())


class ExtractionRun:

    def __init__(
        self,
        graph: ExtractionGraph,
        initial_context: Mapping[str, Any],
        merger: ContextValueMerger
    ) -> None:
        self._graph = graph
        self._context: Context = dict(initial_context)
        self._merger = merger
        self._sorter = graph.create_sorter()
        self._contributions: Dict[str, Dict[int, Any]] = {}
        self._running: Dict[Future, int] = {}

    def execute(self, executor: Executor) -> Context:
        try:
            while self._sorter.is_active():
                self._submit_ready_extractors(executor)
                self._collect_finished_extractors()
        except Exception:
            self._cancel_pending_extractors()
            raise
        return dict(self._context)

    def _submit_ready_extractors(self, executor: Executor) -> None:
        for index in self._sorter.get_ready():
            extractor = self._graph.extractor(index)
            dependencies = {
                key: self._context[key] for key in extractor.dependencies()
            }
            future = executor.submit(run_extractor, extractor, dependencies)
            self._running[future] = index

    def _collect_finished_extractors(self) -> None:
        if not self._running:
            raise ExtractionError("Extraction stalled with no runnable work")
        finished, _ = wait(self._running, return_when=FIRST_COMPLETED)
        for future in finished:
            index = self._running.pop(future)
            self._publish_contributions(index, future.result())
            self._sorter.done(index)

    def _publish_contributions(self, index: int, result: Context) -> None:
        for key, value in result.items():
            contributions = self._contributions.setdefault(key, {})
            contributions[index] = value
            if len(contributions) == self._graph.producer_count(key):
                self._context[key] = self._merger.merge(
                    key,
                    [contributions[i] for i in sorted(contributions)]
                )
            else:
                logger.debug("Key %s awaits more producers", key)

    def _cancel_pending_extractors(self) -> None:
        for future in self._running:
            future.cancel()


class ExtractionPipeline:

    def __init__(
        self,
        extractors: Sequence[Extractor],
        max_workers: int,
        merger: Optional[ContextValueMerger] = None
    ) -> None:
        if max_workers < 1:
            raise ValueError("max_workers must be positive: %d" % max_workers)
        self._extractors = list(extractors)
        self._max_workers = max_workers
        self._merger = ContextValueMerger() if merger is None else merger

    def run(
        self,
        initial_context: Mapping[str, Any],
        required_keys: Iterable[str] = ()
    ) -> Context:
        required = list(required_keys)
        graph = ExtractionGraph(
            self._select_extractors(required),
            initial_context.keys(),
            required
        )
        extraction_run = ExtractionRun(graph, initial_context, self._merger)
        with ThreadPoolExecutor(max_workers=self._max_workers) as executor:
            context = extraction_run.execute(executor)
        missing = [key for key in required if key not in context]
        if missing:
            raise ExtractionError("Extraction did not produce %s" % missing)
        else:
            return context

    def _select_extractors(self, required_keys: List[str]) -> List[Extractor]:
        if required_keys:
            return select_extractors_needed_for(self._extractors, required_keys)
        else:
            return list(self._extractors)
