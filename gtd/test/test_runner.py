import unittest
from unittest.mock import MagicMock, patch

from gtd.ai_help import request_ai_help
from gtd.context_keys import ContextKey
from gtd.extraction import ExtractionError, Extractor, ExtractorFactory
from gtd.extraction.runner import run_extraction
from gtd.test.test_trello_extractors import card, fake_api
from gtd.trello.extractor_factory import TrelloExtractorFactory


class RecordingExtractor(Extractor):

    def __init__(self, calls, dependencies, key):
        self._calls = calls
        self._dependencies = dependencies
        self._key = key

    def dependencies(self):
        return self._dependencies

    def output(self):
        return [self._key]

    def extract(self, context):
        self._calls.append(self._key)
        return {self._key: [self._key]}


class RecordingFactory(ExtractorFactory):

    def __init__(self, calls):
        self._calls = calls

    def create_extractors(self):
        return [
            RecordingExtractor(self._calls, [], ContextKey.AI_HELP_REQUESTS),
            RecordingExtractor(self._calls, [], ContextKey.REPORT),
        ]


def patched_factories(factories):
    return patch(
        "gtd.extraction.runner.load_extractor_factories",
        return_value=factories
    )


class TestRunExtraction(unittest.TestCase):

    def test_rejects_empty_request(self):
        with self.assertRaises(ValueError):
            run_extraction([])

    def test_runs_only_requested_extractors(self):
        calls = []
        with patched_factories([RecordingFactory(calls)]):
            context = run_extraction([ContextKey.REPORT])
        self.assertEqual(calls, [ContextKey.REPORT])
        self.assertNotIn(ContextKey.AI_HELP_REQUESTS, context)


class TestRequestAiHelp(unittest.TestCase):

    def test_returns_requested_titles(self):
        calls = []
        with patched_factories([RecordingFactory(calls)]):
            requested = request_ai_help()
        self.assertEqual(requested, [ContextKey.AI_HELP_REQUESTS])
        self.assertEqual(calls, [ContextKey.AI_HELP_REQUESTS])

    def test_missing_provider_raises(self):
        with patched_factories([]):
            with self.assertRaises(ExtractionError):
                request_ai_help()

    def test_trello_ai_help_skips_report_extractors(self):
        api = fake_api()
        api.get_default_boards.return_value = ["Work"]
        api.get_open_cards.return_value = [
            card("h", labels=[{"name": "Help"}]),
            card("n"),
        ]
        helper = MagicMock()
        with patch(
            "gtd.trello.extractor_factory.trello_plugin.TrelloAPI",
            return_value=api
        ), patch(
            "gtd.trello.extractor_factory.trello_plugin.ai_enabled",
            True
        ), patch(
            "gtd.trello.extractor_factory.trello_plugin.ai_help",
            helper
        ), patched_factories([TrelloExtractorFactory()]):
            requested = request_ai_help()
        self.assertEqual(requested, ["Card h"])
        helper.assert_called_once()
        api.get_closed_cards.assert_not_called()
        api.get_lists.assert_not_called()


if __name__ == "__main__":
    unittest.main()
