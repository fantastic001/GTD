import datetime
import unittest
from dataclasses import replace
from unittest.mock import patch

from gtd.context_keys import ContextKey, ReportSectionKey
from gtd.domain import Project, ProjectProgress, ProjectStatus, Task
from gtd.extraction import ExtractionPipeline
from gtd.report.extractors.monthly_project_progress import (
    MonthlyProjectProgressExtractor,
)
from gtd.report.extractors.monthly_projects_section import (
    MonthlyProjectsSectionExtractor,
)
from gtd.report.extractors.report import ReportExtractor
from gtd.report.generation import generate_monthly_report_elements
from gtd.report.month import is_in_month, resolve_report_month
from gtd.report.monthly_extractor_factory import MonthlyReportExtractorFactory

MONTH = datetime.date(2026, 10, 1)
IN_MONTH = datetime.date(2026, 10, 15)
BEFORE_MONTH = datetime.date(2026, 9, 20)
AFTER_MONTH = datetime.date(2026, 11, 3)

BASE_TASK = Task(
    source="test",
    identifier="t",
    title="task",
    description="",
    url="https://example.com/t",
    reference="T",
    project="Alpha",
    context="Work",
    labels=(),
    due=None,
    created=None,
    last_activity=None,
    closed_on=None,
    is_closed=True,
    is_planned_this_week=False,
    has_checklist=False,
)


def closed_task(project, closed_on, context="Work") -> Task:
    return replace(
        BASE_TASK,
        project=project,
        context=context,
        closed_on=closed_on
    )


def assess(tasks, closed_projects):
    result = MonthlyProjectProgressExtractor().extract({
        ContextKey.CLOSED_TASKS: tasks,
        ContextKey.CLOSED_PROJECTS: closed_projects,
        ContextKey.REPORT_MONTH: MONTH,
    })
    return {
        p.project.name: p
        for p in result[ContextKey.MONTHLY_PROJECT_PROGRESS]
    }


class TestReportMonth(unittest.TestCase):

    def test_resolves_month_and_year(self):
        today = datetime.date(2026, 11, 6)
        self.assertEqual(resolve_report_month(2026, 10, today), MONTH)
        self.assertEqual(
            resolve_report_month(2025, 3, today),
            datetime.date(2025, 3, 1)
        )

    def test_defaults_to_current_month_and_year(self):
        today = datetime.date(2026, 11, 6)
        self.assertEqual(
            resolve_report_month(0, 0, today),
            datetime.date(2026, 11, 1)
        )
        self.assertEqual(
            resolve_report_month(0, 2, today),
            datetime.date(2026, 2, 1)
        )
        self.assertEqual(
            resolve_report_month(2024, 0, today),
            datetime.date(2024, 11, 1)
        )

    def test_rejects_invalid_month_and_year(self):
        today = datetime.date(2026, 11, 6)
        with self.assertRaises(ValueError):
            resolve_report_month(2026, 13, today)
        with self.assertRaises(ValueError):
            resolve_report_month(2026, -1, today)
        with self.assertRaises(ValueError):
            resolve_report_month(-5, 10, today)

    def test_is_in_month(self):
        self.assertTrue(is_in_month(IN_MONTH, MONTH))
        self.assertFalse(is_in_month(AFTER_MONTH, MONTH))
        self.assertFalse(is_in_month(None, MONTH))


class TestMonthlyProjectProgress(unittest.TestCase):

    def test_project_closed_in_month_is_done(self):
        progress = assess(
            [
                closed_task("Alpha", BEFORE_MONTH),
                closed_task("Alpha", IN_MONTH),
            ],
            [Project("Alpha", "Work")]
        )
        self.assertEqual(progress["Alpha"].status, ProjectStatus.DONE)
        self.assertEqual(progress["Alpha"].closed_on, IN_MONTH)
        self.assertEqual(progress["Alpha"].tasks_done_in_month, 1)

    def test_open_project_with_task_done_is_in_progress(self):
        progress = assess([closed_task("Beta", IN_MONTH)], [])
        self.assertEqual(progress["Beta"].status, ProjectStatus.IN_PROGRESS)
        self.assertIsNone(progress["Beta"].closed_on)

    def test_project_closed_later_is_in_progress(self):
        progress = assess(
            [
                closed_task("Gamma", IN_MONTH),
                closed_task("Gamma", AFTER_MONTH),
            ],
            [Project("Gamma", "Work")]
        )
        self.assertEqual(progress["Gamma"].status, ProjectStatus.IN_PROGRESS)
        self.assertEqual(progress["Gamma"].closed_on, AFTER_MONTH)

    def test_projects_without_activity_in_month_are_skipped(self):
        progress = assess(
            [
                closed_task("Old", BEFORE_MONTH),
                closed_task("Later", AFTER_MONTH),
                closed_task("Unknown", None),
            ],
            [Project("Old", "Work")]
        )
        self.assertEqual(progress, {})

    def test_same_project_name_in_other_context_is_distinct(self):
        progress = MonthlyProjectProgressExtractor().extract({
            ContextKey.CLOSED_TASKS: [
                closed_task("Alpha", IN_MONTH, context="Home"),
            ],
            ContextKey.CLOSED_PROJECTS: [Project("Alpha", "Work")],
            ContextKey.REPORT_MONTH: MONTH,
        })[ContextKey.MONTHLY_PROJECT_PROGRESS]
        self.assertEqual(progress[0].status, ProjectStatus.IN_PROGRESS)

    def test_done_projects_listed_first(self):
        result = MonthlyProjectProgressExtractor().extract({
            ContextKey.CLOSED_TASKS: [
                closed_task("A open", IN_MONTH),
                closed_task("Z closed", IN_MONTH),
            ],
            ContextKey.CLOSED_PROJECTS: [Project("Z closed", "Work")],
            ContextKey.REPORT_MONTH: MONTH,
        })[ContextKey.MONTHLY_PROJECT_PROGRESS]
        self.assertEqual(
            [p.project.name for p in result],
            ["Z closed", "A open"]
        )

    def test_rejects_non_date_month(self):
        with self.assertRaises(TypeError):
            MonthlyProjectProgressExtractor().extract({
                ContextKey.CLOSED_TASKS: [],
                ContextKey.CLOSED_PROJECTS: [],
                ContextKey.REPORT_MONTH: "2026-10",
            })


class TestMonthlyProjectsSection(unittest.TestCase):

    def render(self, progress):
        extractor = MonthlyProjectsSectionExtractor()
        result = extractor.extract({
            ContextKey.MONTHLY_PROJECT_PROGRESS: progress,
            ContextKey.REPORT_MONTH: MONTH,
        })
        return "\n".join(result[ReportSectionKey.MONTHLY_PROJECTS])

    def test_section_per_context_with_table(self):
        html = self.render([
            ProjectProgress(
                Project("<Alpha>", "Work"),
                ProjectStatus.DONE,
                2,
                IN_MONTH
            ),
            ProjectProgress(
                Project("Beta", "Home"),
                ProjectStatus.IN_PROGRESS,
                1,
                None
            ),
        ])
        self.assertIn("<h1>Work: projects in 2026-10</h1>", html)
        self.assertIn("<h1>Home: projects in 2026-10</h1>", html)
        self.assertIn("&lt;Alpha&gt;", html)
        self.assertIn("2026-10-15", html)
        self.assertIn("In progress", html)
        self.assertEqual(html.count("<table"), 2)

    def test_empty_month(self):
        html = self.render([])
        self.assertIn("No projects were done or in progress in 2026-10", html)


class TestMonthlyReportFactory(unittest.TestCase):

    def create(self, flags):
        with patch(
            "gtd.extraction.toggles.get_config_bool",
            side_effect=lambda key, default, doc: flags.get(key, default)
        ):
            return MonthlyReportExtractorFactory().create_extractors()

    def report_extractor(self, extractors):
        return [e for e in extractors if isinstance(e, ReportExtractor)][0]

    def test_produces_monthly_report_key(self):
        report = self.report_extractor(self.create({}))
        self.assertEqual(report.output(), [ContextKey.MONTHLY_REPORT])
        self.assertEqual(
            report.dependencies(),
            [ReportSectionKey.MONTHLY_PROJECTS]
        )

    def test_projects_section_can_be_disabled(self):
        report = self.report_extractor(
            self.create({"monthly_report_show_projects": False})
        )
        self.assertEqual(report.dependencies(), [])

    def test_pipeline_renders_monthly_report(self):
        class FakeDataExtractor(MonthlyProjectProgressExtractor):
            def dependencies(self):
                return []

            def output(self):
                return [ContextKey.CLOSED_TASKS, ContextKey.CLOSED_PROJECTS]

            def extract(self, context):
                return {
                    ContextKey.CLOSED_TASKS: [closed_task("Alpha", IN_MONTH)],
                    ContextKey.CLOSED_PROJECTS: [Project("Alpha", "Work")],
                }

        extractors = [FakeDataExtractor()] + self.create({})
        context = ExtractionPipeline(extractors, max_workers=2).run(
            {ContextKey.REPORT_MONTH: MONTH},
            required_keys=[ContextKey.MONTHLY_REPORT]
        )
        html = "\n".join(context[ContextKey.MONTHLY_REPORT])
        self.assertIn("GTD Monthly Project Report", html)
        self.assertIn("Work: projects in 2026-10", html)
        self.assertIn("<td>Done</td>", html)

    def test_extraction_error_is_rendered(self):
        with patch(
            "gtd.extraction.runner.load_extractor_factories",
            return_value=[]
        ):
            elements = generate_monthly_report_elements(MONTH)
        self.assertEqual(len(elements), 1)
        self.assertIn("ERROR", elements[0])


if __name__ == "__main__":
    unittest.main()
