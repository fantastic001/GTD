import datetime
import json
import unittest
from unittest.mock import patch

from gtd.command_executor import CommandExecutor
from gtd.extraction import Extractor, MissingDependencyError
from gtd.extraction.commands import describe_key_producers, extract_key
from gtd.extraction.introspection import (
    ProducerDescription,
    describe_producers,
)
from gtd.extraction.serialization import format_value
from gtd.test.test_report_extractors import BASE_TASK


class StubExtractor(Extractor):

    def __init__(self, calls, dependencies, key, value):
        self._calls = calls
        self._dependencies = dependencies
        self._key = key
        self._value = value

    def dependencies(self):
        return self._dependencies

    def output(self):
        return [self._key]

    def extract(self, context):
        self._calls.append(self._key)
        return {self._key: self._value}


def stub_extractors(calls):
    return [
        StubExtractor(calls, [], "raw", ["r"]),
        StubExtractor(calls, ["raw"], "open_tasks", [BASE_TASK]),
        StubExtractor(calls, [], "open_tasks", []),
        StubExtractor(calls, ["open_tasks"], "report", ["<p/>"]),
    ]


def patched_extractors(calls):
    return patch(
        "gtd.extraction.runner.load_all_extractors",
        return_value=stub_extractors(calls)
    )


def patched_command_extractors(calls):
    return patch(
        "gtd.extraction.commands.load_all_extractors",
        return_value=stub_extractors(calls)
    )


class TestDescribeProducers(unittest.TestCase):

    def test_lists_every_producer_with_dependencies(self):
        descriptions = describe_producers(stub_extractors([]), "open_tasks")
        self.assertEqual(
            descriptions,
            [
                ProducerDescription("StubExtractor", ("raw",)),
                ProducerDescription("StubExtractor", ()),
            ]
        )
        self.assertEqual(str(descriptions[0]), "StubExtractor <- raw")
        self.assertIn("no dependencies", str(descriptions[1]))

    def test_unknown_key_raises(self):
        with self.assertRaises(MissingDependencyError):
            describe_producers(stub_extractors([]), "nothing")

    def test_key_command(self):
        with patched_command_extractors([]):
            lines = CommandExecutor().key("report")
        self.assertEqual(lines, ["StubExtractor <- open_tasks"])

    def test_key_command_unknown_key(self):
        with patched_command_extractors([]):
            with self.assertRaises(MissingDependencyError):
                describe_key_producers("nothing")

    def test_empty_key_is_rejected(self):
        with self.assertRaises(ValueError):
            describe_key_producers(" ")
        with self.assertRaises(ValueError):
            extract_key("", "")


class TestExtractKey(unittest.TestCase):

    def test_runs_only_extractors_needed_for_key(self):
        calls = []
        with patched_extractors(calls):
            value = CommandExecutor().get("open_tasks")
        self.assertEqual(sorted(calls), ["open_tasks", "open_tasks", "raw"])
        self.assertEqual(value, [BASE_TASK])

    def test_json_format_serializes_dataclasses_and_dates(self):
        with patched_extractors([]):
            output = extract_key("open_tasks", "json")
        decoded = json.loads(output)
        self.assertEqual(decoded[0]["identifier"], BASE_TASK.identifier)
        self.assertEqual(decoded[0]["created"], "2026-01-01T00:00:00")
        self.assertEqual(decoded[0]["labels"], [])

    def test_unsupported_format_fails_before_extraction(self):
        calls = []
        with patched_extractors(calls):
            with self.assertRaises(ValueError):
                extract_key("open_tasks", "xml")
        self.assertEqual(calls, [])

    def test_unknown_key_raises(self):
        with patched_extractors([]):
            with self.assertRaises(MissingDependencyError):
                extract_key("nothing", "")


class TestFormatValue(unittest.TestCase):

    def test_raw_format_returns_value(self):
        value = {"a": 1}
        self.assertIs(format_value(value, ""), value)

    def test_json_handles_sets_and_dates(self):
        output = format_value(
            {"d": datetime.date(2026, 10, 29), "s": {1}},
            "json"
        )
        self.assertEqual(json.loads(output), {"d": "2026-10-29", "s": [1]})

    def test_json_rejects_unknown_objects(self):
        with self.assertRaises(TypeError):
            format_value(object(), "json")


if __name__ == "__main__":
    unittest.main()
