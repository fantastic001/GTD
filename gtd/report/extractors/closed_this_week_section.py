from typing import List

from gtd.context_keys import ContextKey, ReportSectionKey
from gtd.extraction.extractor import Context
from gtd.report.rendering import render_tasks_grouped_by_project
from gtd.report.section_extractor import ReportSectionExtractor

CLOSED_THIS_WEEK_TITLE = "Closed tasks this week"


class ClosedThisWeekSectionExtractor(ReportSectionExtractor):

    def section_key(self) -> str:
        return ReportSectionKey.CLOSED_THIS_WEEK

    def dependencies(self) -> List[str]:
        return [ContextKey.CLOSED_THIS_WEEK_TASKS]

    def render_section(self, context: Context) -> List[str]:
        return render_tasks_grouped_by_project(
            CLOSED_THIS_WEEK_TITLE,
            context[ContextKey.CLOSED_THIS_WEEK_TASKS]
        )
