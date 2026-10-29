import datetime
import unittest
from dataclasses import replace
from unittest.mock import patch

from gtd.context_keys import ContextKey, ReportSectionKey
from gtd.domain import ActionPointSuggestion, Deliverable, Project, Task
from gtd.report.extractor_factory import ReportExtractorFactory
from gtd.report.extractors.action_points_section import (
    ActionPointsSectionExtractor,
)
from gtd.report.extractors.calendar import CalendarExtractor
from gtd.report.extractors.closed_this_week import ClosedThisWeekExtractor
from gtd.report.extractors.closed_this_week_section import (
    ClosedThisWeekSectionExtractor,
)
from gtd.report.extractors.deliverables_section import (
    DeliverablesSectionExtractor,
    linkify,
)
from gtd.report.extractors.due_soon_without_checklist_section import (
    DueSoonWithoutChecklistSectionExtractor,
)
from gtd.report.extractors.due_without_weekly_plan_section import (
    DueWithoutWeeklyPlanSectionExtractor,
)
from gtd.report.extractors.extensions_section import (
    ExtensionsSectionExtractor,
)
from gtd.report.extractors.open_tasks_distribution_section import (
    OpenTasksDistributionSectionExtractor,
)
from gtd.report.extractors.report import ReportExtractor
from gtd.report.extractors.statistics_section import (
    StatisticsSectionExtractor,
)
from gtd.report.extractors.this_week_with_checklist_section import (
    ThisWeekWithChecklistSectionExtractor,
)
from gtd.report.extractors.weekly_score_section import (
    WeeklyScoreSectionExtractor,
)
from gtd.report.generation import generate_report_elements

NOW = datetime.datetime(2026, 10, 29, 12, 0)
WEEK_START = datetime.date(2026, 10, 26)

BASE_TASK = Task(
    source="test",
    identifier="t1",
    title="Write <report>",
    description="",
    url="https://example.com/t1",
    reference="T1",
    project="Backlog",
    context="Work",
    labels=(),
    due=None,
    created=datetime.datetime(2026, 1, 1),
    last_activity=datetime.date(2026, 1, 1),
    closed_on=None,
    is_closed=False,
    is_planned_this_week=False,
    has_checklist=False,
)


def task(**changes) -> Task:
    return replace(BASE_TASK, **changes)


def render(extractor, context):
    result = extractor.extract(context)
    return "\n".join(result[extractor.section_key()])


class TestDataExtractors(unittest.TestCase):

    def test_calendar_computes_monday(self):
        context = CalendarExtractor(lambda: NOW).extract({})
        self.assertEqual(context[ContextKey.WEEK_START], WEEK_START)
        self.assertEqual(context[ContextKey.NOW], NOW)

    def test_closed_this_week_filters_by_closure_date(self):
        recent = task(identifier="r", closed_on=WEEK_START)
        older = task(identifier="o", closed_on=datetime.date(2026, 10, 1))
        unknown = task(identifier="u", closed_on=None)
        result = ClosedThisWeekExtractor().extract({
            ContextKey.CLOSED_TASKS: [recent, older, unknown],
            ContextKey.WEEK_START: WEEK_START,
        })
        self.assertEqual(result[ContextKey.CLOSED_THIS_WEEK_TASKS], [recent])


class TestTaskSections(unittest.TestCase):

    def test_this_week_with_checklist_groups_by_project_and_escapes(self):
        planned = task(is_planned_this_week=True, has_checklist=True)
        html = render(
            ThisWeekWithChecklistSectionExtractor(),
            {ContextKey.OPEN_TASKS: [planned, task(identifier="x")]}
        )
        self.assertIn("<h2>Backlog</h2>", html)
        self.assertIn("Write &lt;report&gt;", html)
        self.assertEqual(html.count("<li>"), 1)

    def test_due_soon_sorted_and_excludes_checklists(self):
        later = task(title="later", due=NOW + datetime.timedelta(days=5))
        sooner = task(title="sooner", due=NOW + datetime.timedelta(days=1))
        with_checklist = task(title="checked", due=NOW, has_checklist=True)
        far = task(title="far", due=NOW + datetime.timedelta(days=30))
        html = render(
            DueSoonWithoutChecklistSectionExtractor(7),
            {
                ContextKey.OPEN_TASKS: [later, with_checklist, far, sooner],
                ContextKey.NOW: NOW,
            }
        )
        self.assertLess(html.index("sooner"), html.index("later"))
        self.assertNotIn("checked", html)
        self.assertNotIn("far", html)

    def test_due_soon_without_tasks_renders_nothing(self):
        html = render(
            DueSoonWithoutChecklistSectionExtractor(7),
            {ContextKey.OPEN_TASKS: [], ContextKey.NOW: NOW}
        )
        self.assertEqual(html, "")

    def test_negative_horizon_is_rejected(self):
        with self.assertRaises(ValueError):
            DueSoonWithoutChecklistSectionExtractor(-1)
        with self.assertRaises(ValueError):
            DueWithoutWeeklyPlanSectionExtractor(-1)

    def test_due_without_weekly_plan_skips_planned(self):
        due = NOW + datetime.timedelta(days=3)
        html = render(
            DueWithoutWeeklyPlanSectionExtractor(14),
            {
                ContextKey.OPEN_TASKS: [
                    task(title="alpha", due=due),
                    task(title="beta", due=due, is_planned_this_week=True),
                ],
                ContextKey.NOW: NOW,
            }
        )
        self.assertIn("alpha", html)
        self.assertNotIn("beta", html)

    def test_closed_this_week_section(self):
        html = render(
            ClosedThisWeekSectionExtractor(),
            {ContextKey.CLOSED_THIS_WEEK_TASKS: [task(project="Done list")]}
        )
        self.assertIn("Closed tasks this week", html)
        self.assertIn("<h2>Done list</h2>", html)

    def test_action_points_section(self):
        suggestions = [
            ActionPointSuggestion(task(), ("step <1>",)),
            ActionPointSuggestion(task(identifier="t2"), ()),
        ]
        html = render(
            ActionPointsSectionExtractor(),
            {ContextKey.SUGGESTED_ACTION_POINTS: suggestions}
        )
        self.assertIn("step &lt;1&gt;", html)
        self.assertIn("No suggestions found", html)


class TestStatisticsSections(unittest.TestCase):

    def context(self, open_tasks, closed_tasks, closed_this_week):
        return {
            ContextKey.OPEN_TASKS: open_tasks,
            ContextKey.CLOSED_TASKS: closed_tasks,
            ContextKey.CLOSED_THIS_WEEK_TASKS: closed_this_week,
            ContextKey.NOW: NOW,
            ContextKey.WEEK_START: WEEK_START,
        }

    def test_without_closed_tasks(self):
        html = render(
            StatisticsSectionExtractor(),
            self.context([task()], [], [])
        )
        self.assertIn("Number of open tasks: 1", html)
        self.assertIn("No tasks closed yet", html)

    def test_with_closed_tasks(self):
        new_task = task(created=datetime.datetime(2026, 10, 27))
        closed = task(closed_on=WEEK_START, is_closed=True, last_activity=None)
        html = render(
            StatisticsSectionExtractor(),
            self.context([task(), new_task], [closed], [closed])
        )
        self.assertIn("Tasks opened this week: 1", html)
        self.assertIn("Tasks closed this week: 1", html)
        self.assertIn("Net closure this week: 0", html)
        self.assertIn("Remaining days in year: 64", html)

    def test_weekly_score(self):
        html = render(
            WeeklyScoreSectionExtractor(),
            {ContextKey.WEEKLY_SCORE: 9}
        )
        self.assertIn("Score for this week: 9", html)

    def test_distribution_per_project_for_single_context(self):
        html = render(
            OpenTasksDistributionSectionExtractor(),
            {
                ContextKey.OPEN_TASKS: [task(), task(identifier="t2")],
                ContextKey.PROJECTS: [
                    Project("Backlog", "Work"),
                    Project("Empty", "Work"),
                ],
                ContextKey.CONTEXTS: ["Work"],
            }
        )
        self.assertIn("per project", html)
        self.assertIn("Empty", html)

    def test_distribution_per_context_skips_empty_contexts(self):
        html = render(
            OpenTasksDistributionSectionExtractor(),
            {
                ContextKey.OPEN_TASKS: [task()],
                ContextKey.PROJECTS: [],
                ContextKey.CONTEXTS: ["Work", "Home"],
            }
        )
        self.assertIn("per context", html)
        self.assertNotIn("Home", html)


class TestDeliverablesSection(unittest.TestCase):

    def test_linkify_converts_links_and_escapes(self):
        self.assertEqual(
            linkify("see https://x.io/a <b>"),
            'see <a href="https://x.io/a">https://x.io/a</a> &lt;b&gt;'
        )
        self.assertEqual(
            linkify("[doc](https://x.io/d)"),
            '<a href="https://x.io/d">doc</a>'
        )
        self.assertEqual(linkify("plain"), "plain")

    def test_renders_evidence_and_warns_on_missing(self):
        deliverables = [
            Deliverable(task(), ("https://files/a",), ("done",)),
            Deliverable(task(identifier="c", is_closed=True), (), ()),
            Deliverable(task(identifier="o", project="Idle"), (), ()),
        ]
        html = render(
            DeliverablesSectionExtractor(),
            {ContextKey.DELIVERABLES: deliverables}
        )
        self.assertIn("Deliverables this week for Work", html)
        self.assertIn("https://files/a", html)
        self.assertIn("Write &lt;report&gt;: done", html)
        self.assertEqual(html.count("Without deliverables"), 1)
        self.assertNotIn("Idle", html)


class TestReportExtractor(unittest.TestCase):

    def test_concatenates_sections_in_order(self):
        extractor = ReportExtractor("My <Report>", ["b", "a"])
        self.assertEqual(extractor.dependencies(), ["b", "a"])
        report = extractor.extract({"a": ["A"], "b": ["B"]})[ContextKey.REPORT]
        self.assertIn("<h1>My &lt;Report&gt;</h1>", report)
        self.assertLess(report.index("B"), report.index("A"))
        self.assertEqual(report[-1], "</html>")

    def test_rejects_duplicate_sections(self):
        with self.assertRaises(ValueError):
            ReportExtractor("t", ["a", "a"])

    def test_extensions_section_uses_loader(self):
        extractor = ExtensionsSectionExtractor(lambda: ["<p>ext</p>"])
        self.assertEqual(
            extractor.extract({}),
            {ReportSectionKey.EXTENSIONS: ["<p>ext</p>"]}
        )


class TestReportExtractorFactory(unittest.TestCase):

    def create(self, flags):
        with patch(
            "gtd.extraction.toggles.get_config_bool",
            side_effect=lambda key, default, doc: flags.get(key, default)
        ):
            return ReportExtractorFactory().create_extractors()

    def report_dependencies(self, extractors):
        report = [e for e in extractors if isinstance(e, ReportExtractor)]
        return report[0].dependencies()

    def test_default_sections(self):
        sections = self.report_dependencies(self.create({}))
        self.assertIn(ReportSectionKey.DELIVERABLES, sections)
        self.assertNotIn(ReportSectionKey.CLOSED_THIS_WEEK, sections)
        self.assertNotIn(ReportSectionKey.WEEKLY_SCORE, sections)
        self.assertNotIn(ReportSectionKey.ACTION_POINTS, sections)

    def test_flags_switch_sections(self):
        sections = self.report_dependencies(self.create({
            "report_deliverables": False,
            "report_score": True,
            "report_this_week_without_checklist": True,
            "report_show_statistics": False,
        }))
        self.assertIn(ReportSectionKey.CLOSED_THIS_WEEK, sections)
        self.assertIn(ReportSectionKey.WEEKLY_SCORE, sections)
        self.assertIn(ReportSectionKey.ACTION_POINTS, sections)
        self.assertNotIn(ReportSectionKey.DELIVERABLES, sections)
        self.assertNotIn(ReportSectionKey.STATISTICS, sections)


class TestGenerateReportElements(unittest.TestCase):

    def test_extraction_error_is_rendered(self):
        with patch(
            "gtd.extraction.runner.load_extractor_factories",
            return_value=[]
        ):
            elements = generate_report_elements()
        self.assertEqual(len(elements), 1)
        self.assertIn("ERROR", elements[0])
        self.assertIn("report", elements[0])


if __name__ == "__main__":
    unittest.main()
