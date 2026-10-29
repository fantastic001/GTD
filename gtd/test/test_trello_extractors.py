import datetime
import unittest
from unittest.mock import MagicMock, patch

from gtd.context_keys import ContextKey
from gtd.domain import Project
from gtd.extraction import ExtractionPipeline
from gtd.report.extractor_factory import ReportExtractorFactory
from gtd.trello.context_keys import TrelloContextKey
from gtd.trello.extractor_factory import TrelloExtractorFactory
from gtd.trello.extractors.action_points import TrelloActionPointsExtractor
from gtd.trello.extractors.ai_help import TrelloAiHelpExtractor
from gtd.trello.extractors.boards import TrelloBoardsExtractor
from gtd.trello.extractors.closed_cards import TrelloClosedCardsExtractor
from gtd.trello.extractors.closed_lists import TrelloClosedListExtractor
from gtd.trello.extractors.closed_tasks import TrelloClosedTasksExtractor
from gtd.trello.extractors.closure_dates import TrelloClosureDatesExtractor
from gtd.trello.extractors.deliverables import TrelloDeliverablesExtractor
from gtd.trello.extractors.lists import TrelloListExtractor
from gtd.trello.extractors.open_cards import TrelloOpenCardsExtractor
from gtd.trello.extractors.open_tasks import TrelloOpenTasksExtractor
from gtd.trello.extractors.score import TrelloScoreExtractor
from gtd.trello.task_mapping import TRELLO_SOURCE, TrelloCardToTaskMapper

WEEK_START = datetime.date(2026, 10, 26)
BOARD = {"id": "B1", "name": "Work"}
BACKLOG = {"id": "L1", "name": " Backlog ", "idBoard": "B1"}
ARCHIVE = {"id": "L2", "name": "Archive", "idBoard": "B1"}


def card(identifier, **fields):
    defaults = {
        "id": identifier,
        "name": "Card " + identifier,
        "desc": "",
        "shortUrl": "https://trello.com/c/" + identifier,
        "shortLink": identifier,
        "idList": "L1",
        "idBoard": "B1",
        "labels": [],
        "due": None,
        "dateLastActivity": "2026-10-27T10:00:00.000Z",
        "idChecklists": [],
        "closed": False,
    }
    defaults.update(fields)
    return defaults


def fake_api():
    api = MagicMock()
    api.get_board.return_value = BOARD
    api.get_lists.return_value = [BACKLOG]
    api.get_closed_lists.return_value = [ARCHIVE]
    api.get_creation_date.return_value = datetime.datetime(2026, 1, 1)
    api.is_card_closed.side_effect = lambda c: c.get("closed", False)
    api.get_list_name.return_value = "Elsewhere"
    api.get_board_name.return_value = "Other board"
    api.has_label.side_effect = (
        lambda c, name: any(l["name"] == name for l in c["labels"])
    )
    return api


class TestTaskMapping(unittest.TestCase):

    def test_maps_card_fields(self):
        mapper = TrelloCardToTaskMapper(fake_api(), [BOARD], [BACKLOG], "Now")
        mapped = mapper.map_card(
            card(
                "c1",
                labels=[{"name": "Now"}],
                idChecklists=["x"],
                due="2026-10-30T10:00:00.000Z",
            ),
            {"c1": WEEK_START}
        )
        self.assertEqual(mapped.source, TRELLO_SOURCE)
        self.assertEqual(mapped.project, "Backlog")
        self.assertEqual(mapped.context, "Work")
        self.assertTrue(mapped.is_planned_this_week)
        self.assertTrue(mapped.has_checklist)
        self.assertEqual(mapped.closed_on, WEEK_START)
        self.assertEqual(mapped.last_activity, datetime.date(2026, 10, 27))
        self.assertIsInstance(mapped.due, datetime.datetime)

    def test_falls_back_to_api_for_unknown_list_and_board(self):
        mapper = TrelloCardToTaskMapper(fake_api(), [], [], "Now")
        mapped = mapper.map_card(
            card("c1", dateLastActivity=None, idChecklists=None),
            {}
        )
        self.assertEqual(mapped.project, "Elsewhere")
        self.assertEqual(mapped.context, "Other board")
        self.assertIsNone(mapped.last_activity)
        self.assertFalse(mapped.has_checklist)


class TestRawTrelloExtractors(unittest.TestCase):

    def setUp(self):
        self.api = fake_api()
        self.boards = ["Work"]

    def test_boards(self):
        result = TrelloBoardsExtractor(self.api, self.boards).extract({})
        self.assertEqual(result[TrelloContextKey.BOARDS], [BOARD])
        self.assertEqual(result[ContextKey.CONTEXTS], ["Work"])

    def test_lists_provide_projects(self):
        result = TrelloListExtractor(self.api, self.boards).extract({})
        self.assertEqual(result[TrelloContextKey.LISTS], [BACKLOG])
        self.assertEqual(
            result[ContextKey.PROJECTS],
            [Project("Backlog", "Work")]
        )
        self.api.get_lists.assert_called_once_with(board_name="Work")

    def test_closed_lists_and_cards(self):
        self.api.get_open_cards.return_value = [card("o")]
        self.api.get_closed_cards.return_value = [card("c")]
        closed_lists = TrelloClosedListExtractor(self.api, self.boards)
        open_cards = TrelloOpenCardsExtractor(self.api, self.boards)
        closed_cards = TrelloClosedCardsExtractor(self.api, self.boards)
        self.assertEqual(
            closed_lists.extract({})[TrelloContextKey.CLOSED_LISTS],
            [ARCHIVE]
        )
        self.assertEqual(
            open_cards.extract({})[TrelloContextKey.OPEN_CARDS][0]["id"],
            "o"
        )
        self.assertEqual(
            closed_cards.extract({})[TrelloContextKey.CLOSED_CARDS][0]["id"],
            "c"
        )

    def test_closure_dates(self):
        with patch(
            "gtd.trello.extractors.closure_dates.get_closed_dates",
            return_value={"c": WEEK_START}
        ):
            result = TrelloClosureDatesExtractor(self.api).extract(
                {TrelloContextKey.CLOSED_CARDS: [card("c")]}
            )
        self.assertEqual(
            result[TrelloContextKey.CLOSURE_DATES],
            {"c": WEEK_START}
        )

    def test_open_and_closed_tasks(self):
        open_result = TrelloOpenTasksExtractor(self.api, "Now").extract({
            TrelloContextKey.BOARDS: [BOARD],
            TrelloContextKey.LISTS: [BACKLOG],
            TrelloContextKey.OPEN_CARDS: [card("o")],
        })
        closed_result = TrelloClosedTasksExtractor(self.api, "Now").extract({
            TrelloContextKey.BOARDS: [BOARD],
            TrelloContextKey.LISTS: [BACKLOG],
            TrelloContextKey.CLOSED_LISTS: [ARCHIVE],
            TrelloContextKey.CLOSED_CARDS: [
                card("c", idList="L2", closed=True)
            ],
            TrelloContextKey.CLOSURE_DATES: {"c": WEEK_START},
        })
        self.assertEqual(open_result[ContextKey.OPEN_TASKS][0].identifier, "o")
        closed = closed_result[ContextKey.CLOSED_TASKS][0]
        self.assertEqual(closed.project, "Archive")
        self.assertTrue(closed.is_closed)
        self.assertEqual(closed.closed_on, WEEK_START)


class TestDerivedTrelloExtractors(unittest.TestCase):

    def setUp(self):
        self.api = fake_api()
        mapper = TrelloCardToTaskMapper(self.api, [BOARD], [BACKLOG], "Now")
        self.primary = mapper.map_card(
            card("p", labels=[{"name": "Primary"}]),
            {}
        )
        self.other = mapper.map_card(card("x"), {})

    def test_deliverables_only_for_primary_tasks(self):
        self.api.get_attachments.return_value = [{"url": "https://f/1"}]
        self.api.get_comments.return_value = [
            {"text": "new", "date": "2026-10-27T10:00:00.000Z"},
            {"text": "old", "date": "2026-10-01T10:00:00.000Z"},
            {"text": "bad", "date": "garbage"},
        ]
        result = TrelloDeliverablesExtractor(self.api, "Primary").extract({
            ContextKey.OPEN_TASKS: [self.primary, self.other],
            ContextKey.CLOSED_THIS_WEEK_TASKS: [],
            ContextKey.WEEK_START: WEEK_START,
        })
        deliverables = result[ContextKey.DELIVERABLES]
        self.assertEqual(len(deliverables), 1)
        self.assertEqual(deliverables[0].attachment_urls, ("https://f/1",))
        self.assertEqual(deliverables[0].comments, ("new",))

    def test_score_counts_cards_closed_this_week(self):
        cards = [card("new"), card("old"), card("unknown")]
        dates = {"new": WEEK_START, "old": datetime.date(2026, 1, 1)}
        with patch(
            "gtd.trello.extractors.score.score_closed_cards",
            return_value=5
        ) as score:
            result = TrelloScoreExtractor(self.api).extract({
                TrelloContextKey.CLOSED_CARDS: cards,
                TrelloContextKey.CLOSURE_DATES: dates,
                ContextKey.WEEK_START: WEEK_START,
            })
        self.assertEqual(result[ContextKey.WEEKLY_SCORE], 5)
        scored_cards = score.call_args.args[1]
        self.assertEqual([c["id"] for c in scored_cards], ["new"])

    def test_action_points_stored_as_checklist(self):
        planned = TrelloCardToTaskMapper(
            self.api, [BOARD], [BACKLOG], "Now"
        ).map_card(card("w", labels=[{"name": "Now"}]), {})
        self.api.add_checklist.return_value = {"id": "chk"}
        advisor = MagicMock(side_effect=[["step 1", "step 2"]])
        extractor = TrelloActionPointsExtractor(
            self.api,
            advisor,
            lambda: "credentials",
            lambda project: "context of " + project
        )
        result = extractor.extract(
            {ContextKey.OPEN_TASKS: [planned, self.other]}
        )
        suggestions = result[ContextKey.SUGGESTED_ACTION_POINTS]
        self.assertEqual(suggestions[0].action_points, ("step 1", "step 2"))
        self.assertIn("context of Backlog", advisor.call_args.args[0])
        self.api.add_checklist.assert_called_once_with("w", "Checklist")
        self.assertEqual(self.api.add_checklist_item.call_count, 2)

    def test_action_points_without_planned_tasks(self):
        loader = MagicMock()
        extractor = TrelloActionPointsExtractor(
            self.api, MagicMock(), loader, MagicMock()
        )
        result = extractor.extract({ContextKey.OPEN_TASKS: [self.other]})
        self.assertEqual(result[ContextKey.SUGGESTED_ACTION_POINTS], [])
        loader.assert_not_called()

    def test_action_points_without_suggestions(self):
        planned = TrelloCardToTaskMapper(
            self.api, [BOARD], [BACKLOG], "Now"
        ).map_card(card("w", labels=[{"name": "Now"}]), {})
        extractor = TrelloActionPointsExtractor(
            self.api, lambda prompt, key: [], lambda: None, lambda p: ""
        )
        result = extractor.extract({ContextKey.OPEN_TASKS: [planned]})
        self.assertEqual(
            result[ContextKey.SUGGESTED_ACTION_POINTS][0].action_points,
            ()
        )
        self.api.add_checklist.assert_not_called()

    def test_ai_help_requests(self):
        helper = MagicMock()
        cards = [card("h", labels=[{"name": "Help"}]), card("n")]
        result = TrelloAiHelpExtractor(self.api, "Help", helper).extract(
            {TrelloContextKey.OPEN_CARDS: cards}
        )
        self.assertEqual(result[ContextKey.AI_HELP_REQUESTS], ["Card h"])
        helper.assert_called_once_with(self.api, cards, "Help")


class TestTrelloReportPipeline(unittest.TestCase):

    def config_bool(self, key, default, doc):
        return {"report_score": True}.get(key, default)

    def build_extractors(self, api):
        with patch(
            "gtd.trello.extractor_factory.trello_plugin.TrelloAPI",
            return_value=api
        ), patch(
            "gtd.extraction.toggles.get_config_bool",
            side_effect=self.config_bool
        ), patch(
            "gtd.trello.extractor_factory.trello_plugin.ai_enabled",
            False
        ), patch(
            "gtd.report.extractor_factory.load_extensions",
            return_value=["<p>extension</p>"]
        ):
            return (
                TrelloExtractorFactory().create_extractors()
                + ReportExtractorFactory().create_extractors()
            )

    def test_full_report_from_trello_data(self):
        api = fake_api()
        api.get_default_boards.return_value = ["Work"]
        api.get_open_cards.return_value = [
            card("o1", labels=[{"name": "This week"}], idChecklists=["k"]),
            card("o2", labels=[{"name": "Primary"}]),
        ]
        api.get_closed_cards.return_value = [card("c1", closed=True)]
        api.get_closure_date.return_value = datetime.date.today()
        api.get_attachments.return_value = []
        api.get_comments.return_value = []
        extractors = self.build_extractors(api)
        with patch(
            "gtd.trello.extractors.score.score_closed_cards",
            return_value=3
        ):
            context = ExtractionPipeline(extractors, max_workers=4).run(
                {},
                required_keys=[ContextKey.REPORT]
            )
        html = "\n".join(context[ContextKey.REPORT])
        self.assertIn("Tasks this week with checklist", html)
        self.assertIn("Number of open tasks: 2", html)
        self.assertIn("Tasks closed this week: 1", html)
        self.assertIn("Score for this week: 3", html)
        self.assertIn("Deliverables this week for Work", html)
        self.assertIn("<p>extension</p>", html)


if __name__ == "__main__":
    unittest.main()
