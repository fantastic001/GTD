import threading
import types
import unittest
from abc import abstractmethod
from typing import Callable, List, Optional
from unittest.mock import patch

from gtd.extraction import (
    ConflictingOutputError,
    CyclicDependencyError,
    ExtractionError,
    ExtractionPipeline,
    Extractor,
    ExtractorContractError,
    ExtractorFactory,
    ExtractorFailedError,
    MissingDependencyError,
    create_extractors,
)
from gtd.extraction.loader import find_factory_classes, load_extractor_factories
from gtd.extraction.merge import ContextValueMerger
from gtd.extraction.toggles import (
    AlwaysEnabled,
    AvailabilityToggle,
    ConfigFlag,
    Inverted,
    create_enabled_extractors,
)

BARRIER_TIMEOUT_SECONDS = 5


class FunctionExtractor(Extractor):

    def __init__(
        self,
        dependencies: List[str],
        output: List[str],
        compute: Callable[[dict], dict],
        label: Optional[str] = None
    ) -> None:
        self._dependencies = dependencies
        self._output = output
        self._compute = compute
        self._label = label

    def dependencies(self) -> List[str]:
        return self._dependencies

    def output(self) -> List[str]:
        return self._output

    def extract(self, context: dict) -> dict:
        return self._compute(context)

    def name(self) -> str:
        return self._label or super().name()


def constant(key: str, value) -> FunctionExtractor:
    return FunctionExtractor([], [key], lambda _: {key: value}, key)


def run(extractors, initial=None, required=()):
    pipeline = ExtractionPipeline(extractors, max_workers=4)
    return pipeline.run(initial or {}, required_keys=required)


class TestExtractionPipeline(unittest.TestCase):

    def test_runs_dependent_extractors_in_topological_order(self):
        extractors = [
            FunctionExtractor(
                ["projects"],
                ["report"],
                lambda c: {"report": ["n=%d" % len(c["projects"])]}
            ),
            constant("projects", ["a", "b"]),
        ]
        context = run(extractors, required=["report"])
        self.assertEqual(context["report"], ["n=2"])
        self.assertEqual(context["projects"], ["a", "b"])

    def test_extractor_receives_only_declared_dependencies(self):
        seen = {}

        def capture(context):
            seen.update(context)
            return {"b": 1}

        extractors = [
            constant("a", 1),
            constant("unrelated", 2),
            FunctionExtractor(["a"], ["b"], capture),
        ]
        run(extractors)
        self.assertEqual(seen, {"a": 1})

    def test_independent_extractors_run_concurrently(self):
        barrier = threading.Barrier(2, timeout=BARRIER_TIMEOUT_SECONDS)

        def meet(key):
            return lambda _: (barrier.wait(), {key: True})[1]

        extractors = [
            FunctionExtractor([], ["left"], meet("left")),
            FunctionExtractor([], ["right"], meet("right")),
        ]
        context = run(extractors)
        self.assertTrue(context["left"] and context["right"])

    def test_initial_context_satisfies_dependencies(self):
        extractor = FunctionExtractor(
            ["seed"],
            ["doubled"],
            lambda c: {"doubled": c["seed"] * 2}
        )
        self.assertEqual(run([extractor], {"seed": 4})["doubled"], 8)

    def test_merges_lists_from_multiple_providers_in_order(self):
        extractors = [
            constant("open_tasks", ["trello"]),
            constant("open_tasks", ["jira"]),
            FunctionExtractor(
                ["open_tasks"],
                ["count"],
                lambda c: {"count": len(c["open_tasks"])}
            ),
        ]
        context = run(extractors)
        self.assertEqual(context["open_tasks"], ["trello", "jira"])
        self.assertEqual(context["count"], 2)

    def test_missing_dependency_is_reported_before_running(self):
        calls = []
        extractors = [
            FunctionExtractor([], ["a"], lambda _: calls.append(1) or {"a": 1}),
            FunctionExtractor(["nowhere"], ["b"], lambda _: {"b": 1}, "B"),
        ]
        with self.assertRaises(MissingDependencyError) as raised:
            run(extractors)
        self.assertIn("B requires 'nowhere'", str(raised.exception))
        self.assertEqual(calls, [])

    def test_missing_required_key(self):
        with self.assertRaises(MissingDependencyError):
            run([constant("a", 1)], required=["report"])

    def test_cycle_is_detected(self):
        extractors = [
            FunctionExtractor(["b"], ["a"], lambda _: {"a": 1}, "A"),
            FunctionExtractor(["a"], ["b"], lambda _: {"b": 1}, "B"),
        ]
        with self.assertRaises(CyclicDependencyError):
            run(extractors)

    def test_output_conflicting_with_initial_context(self):
        with self.assertRaises(ConflictingOutputError):
            run([constant("a", 1)], {"a": 0})

    def test_duplicate_output_keys_violate_contract(self):
        extractor = FunctionExtractor([], ["a", "a"], lambda _: {"a": 1})
        with self.assertRaises(ExtractorContractError):
            run([extractor])

    def test_result_with_undeclared_keys_violates_contract(self):
        extractor = FunctionExtractor([], ["a"], lambda _: {"b": 1})
        with self.assertRaises(ExtractorContractError):
            run([extractor])

    def test_non_mapping_result_violates_contract(self):
        extractor = FunctionExtractor([], ["a"], lambda _: ["a"])
        with self.assertRaises(ExtractorContractError):
            run([extractor])

    def test_failing_extractor_stops_dependents(self):
        dependent_calls = []

        def fail(_):
            raise RuntimeError("boom")

        extractors = [
            FunctionExtractor([], ["a"], fail, "Failing"),
            FunctionExtractor(
                ["a"],
                ["b"],
                lambda _: dependent_calls.append(1) or {"b": 1}
            ),
        ]
        with self.assertRaises(ExtractorFailedError) as raised:
            run(extractors)
        self.assertIn("Failing failed: boom", str(raised.exception))
        self.assertEqual(dependent_calls, [])

    def test_rejects_non_positive_workers(self):
        with self.assertRaises(ValueError):
            ExtractionPipeline([], max_workers=0)

    def test_empty_pipeline_returns_initial_context(self):
        self.assertEqual(run([], {"a": 1}), {"a": 1})


class TestRequiredKeyPruning(unittest.TestCase):

    def recording(self, calls, dependencies, key):
        return FunctionExtractor(
            dependencies,
            [key],
            lambda _: calls.append(key) or {key: key},
            key
        )

    def test_runs_only_transitive_producers_of_required_keys(self):
        calls = []
        extractors = [
            self.recording(calls, [], "raw"),
            self.recording(calls, ["raw"], "tasks"),
            self.recording(calls, ["tasks"], "report"),
            self.recording(calls, [], "unused"),
            self.recording(calls, ["unused"], "side_effect"),
        ]
        context = run(extractors, required=["report"])
        self.assertEqual(calls, ["raw", "tasks", "report"])
        self.assertNotIn("unused", context)
        self.assertNotIn("side_effect", context)

    def test_unneeded_extractor_with_missing_dependency_is_ignored(self):
        calls = []
        extractors = [
            self.recording(calls, [], "report"),
            self.recording(calls, ["nowhere"], "orphan"),
        ]
        context = run(extractors, required=["report"])
        self.assertEqual(context["report"], "report")
        self.assertEqual(calls, ["report"])

    def test_all_producers_of_a_needed_key_run(self):
        extractors = [
            constant("open_tasks", ["trello"]),
            constant("open_tasks", ["jira"]),
            FunctionExtractor(
                ["open_tasks"],
                ["report"],
                lambda c: {"report": c["open_tasks"]}
            ),
        ]
        context = run(extractors, required=["report"])
        self.assertEqual(context["report"], ["trello", "jira"])

    def test_required_key_satisfied_by_initial_context(self):
        calls = []
        extractors = [self.recording(calls, [], "other")]
        context = run(extractors, {"report": ["seed"]}, required=["report"])
        self.assertEqual(context, {"report": ["seed"]})
        self.assertEqual(calls, [])

    def test_without_required_keys_all_extractors_run(self):
        calls = []
        run([self.recording(calls, [], "a"), self.recording(calls, [], "b")])
        self.assertEqual(sorted(calls), ["a", "b"])


class TestContextValueMerger(unittest.TestCase):

    def setUp(self):
        self.merger = ContextValueMerger()

    def test_single_value_is_returned_unchanged(self):
        value = object()
        self.assertIs(self.merger.merge("k", [value]), value)

    def test_no_values_is_an_error(self):
        with self.assertRaises(ValueError):
            self.merger.merge("k", [])

    def test_dicts_are_united(self):
        merged = self.merger.merge("k", [{"a": 1}, {"b": 2}])
        self.assertEqual(merged, {"a": 1, "b": 2})

    def test_overlapping_dicts_conflict(self):
        with self.assertRaises(ConflictingOutputError):
            self.merger.merge("k", [{"a": 1}, {"a": 2}])

    def test_numbers_are_summed(self):
        self.assertEqual(self.merger.merge("score", [3, 4]), 7)

    def test_mixed_types_conflict(self):
        with self.assertRaises(ConflictingOutputError):
            self.merger.merge("k", [[1], {"a": 1}])

    def test_unmergeable_type_conflicts(self):
        with self.assertRaises(ConflictingOutputError):
            self.merger.merge("k", ["a", "b"])


class AbstractFactory(ExtractorFactory):

    @abstractmethod
    def helper(self):
        ...


class SampleFactory(ExtractorFactory):

    def create_extractors(self):
        return [constant("sample", 1)]


class BrokenFactory(ExtractorFactory):

    def create_extractors(self):
        raise ValueError("misconfigured")


class TestLoader(unittest.TestCase):

    def test_finds_concrete_factories_once(self):
        first = types.ModuleType("first")
        first.SampleFactory = SampleFactory
        first.AbstractFactory = AbstractFactory
        first.ExtractorFactory = ExtractorFactory
        second = types.ModuleType("second")
        second.Alias = SampleFactory
        self.assertEqual(find_factory_classes([first, second]), [SampleFactory])

    def test_create_extractors_flattens_factories(self):
        extractors = create_extractors([SampleFactory(), SampleFactory()])
        self.assertEqual(len(extractors), 2)

    def test_factory_failure_becomes_extraction_error(self):
        with self.assertRaises(ExtractionError) as raised:
            create_extractors([BrokenFactory()])
        self.assertIn("BrokenFactory", str(raised.exception))

    def test_loads_factories_from_builtin_and_plugin_modules(self):
        plugin = types.ModuleType("plugin")
        plugin.SampleFactory = SampleFactory
        with patch(
            "gtd.extraction.loader.load_plugins",
            return_value=[("plugin", plugin)]
        ), patch(
            "gtd.extraction.loader.get_config_list",
            return_value=[]
        ):
            factories = load_extractor_factories()
        self.assertEqual([type(f) for f in factories], [SampleFactory])


class TestToggles(unittest.TestCase):

    def test_create_enabled_extractors_respects_toggles(self):
        table = [
            (AlwaysEnabled(), lambda: constant("a", 1)),
            (Inverted(AlwaysEnabled()), lambda: constant("b", 1)),
            (AvailabilityToggle(lambda: True), lambda: constant("c", 1)),
        ]
        names = [e.name() for e in create_enabled_extractors(table)]
        self.assertEqual(names, ["a", "c"])

    def test_config_flag_reads_configuration(self):
        with patch(
            "gtd.extraction.toggles.get_config_bool",
            return_value=False
        ) as config:
            self.assertFalse(ConfigFlag("flag", True, "doc").is_enabled())
        config.assert_called_once_with("flag", True, "doc")


if __name__ == "__main__":
    unittest.main()
