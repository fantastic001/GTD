from typing import List

from gtd.context_keys import ContextKey, ReportSectionKey
from gtd.extraction.extractor import Context
from gtd.report.rendering import render_tasks_grouped_by_project
from gtd.report.section_extractor import ReportSectionExtractor

THIS_WEEK_WITH_CHECKLIST_TITLE = "Tasks this week with checklist"


class ThisWeekWithChecklistSectionExtractor(ReportSectionExtractor):

    def section_key(self) -> str:
        return ReportSectionKey.THIS_WEEK_WITH_CHECKLIST

    def dependencies(self) -> List[str]:
        return [ContextKey.OPEN_TASKS]

    def render_section(self, context: Context) -> List[str]:
        planned_tasks = [
            task for task in context[ContextKey.OPEN_TASKS]
            if task.is_planned_this_week and task.has_checklist
        ]
        return render_tasks_grouped_by_project(
            THIS_WEEK_WITH_CHECKLIST_TITLE,
            planned_tasks
        )
