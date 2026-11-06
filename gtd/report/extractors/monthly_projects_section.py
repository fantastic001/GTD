import html
from typing import Dict, List, Sequence

from gtd.context_keys import ContextKey, ReportSectionKey
from gtd.domain import ProjectProgress
from gtd.extraction.extractor import Context
from gtd.report.month import format_report_month
from gtd.report.rendering import group_by
from gtd.report.section_extractor import ReportSectionExtractor
from gtd.style import paragraph, section, table

CONTEXT_SECTION_TITLE = "%s: projects in %s"
NO_PROJECTS_MESSAGE = "No projects were done or in progress in %s"
PROJECT_COLUMN = "Project"
STATUS_COLUMN = "Status"
TASKS_DONE_COLUMN = "Tasks done in month"
CLOSED_ON_COLUMN = "Project closed on"
NOT_CLOSED_MARK = "-"


def tabulate_project_progress(
    progress: Sequence[ProjectProgress]
) -> List[Dict[str, object]]:
    return [
        {
            PROJECT_COLUMN: html.escape(p.project.name),
            STATUS_COLUMN: p.status.value,
            TASKS_DONE_COLUMN: p.tasks_done_in_month,
            CLOSED_ON_COLUMN: (
                p.closed_on.isoformat() if p.closed_on else NOT_CLOSED_MARK
            ),
        }
        for p in progress
    ]


class MonthlyProjectsSectionExtractor(ReportSectionExtractor):

    def section_key(self) -> str:
        return ReportSectionKey.MONTHLY_PROJECTS

    def dependencies(self) -> List[str]:
        return [ContextKey.MONTHLY_PROJECT_PROGRESS, ContextKey.REPORT_MONTH]

    def render_section(self, context: Context) -> List[str]:
        month = format_report_month(context[ContextKey.REPORT_MONTH])
        by_context = group_by(
            context[ContextKey.MONTHLY_PROJECT_PROGRESS],
            lambda p: p.project.context
        )
        if by_context:
            return [
                element
                for context_name, progress in by_context.items()
                for element in (
                    section(CONTEXT_SECTION_TITLE % (
                        html.escape(context_name),
                        month
                    )),
                    table(tabulate_project_progress(progress)),
                )
            ]
        else:
            return [paragraph(NO_PROJECTS_MESSAGE % month)]
