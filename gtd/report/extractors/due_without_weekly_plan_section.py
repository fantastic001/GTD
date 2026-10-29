from typing import List

from gtd.context_keys import ContextKey, ReportSectionKey
from gtd.extraction.extractor import Context
from gtd.report.rendering import render_task_list_section
from gtd.report.section_extractor import ReportSectionExtractor

DUE_WITHOUT_WEEKLY_PLAN_TITLE = "Tasks due in %d days not planned for this week"


class DueWithoutWeeklyPlanSectionExtractor(ReportSectionExtractor):

    def __init__(self, horizon_days: int) -> None:
        if horizon_days < 0:
            raise ValueError("horizon_days must not be negative")
        self._horizon_days = horizon_days

    def section_key(self) -> str:
        return ReportSectionKey.DUE_WITHOUT_WEEKLY_PLAN

    def dependencies(self) -> List[str]:
        return [ContextKey.OPEN_TASKS, ContextKey.NOW]

    def render_section(self, context: Context) -> List[str]:
        now = context[ContextKey.NOW]
        unplanned = [
            task for task in context[ContextKey.OPEN_TASKS]
            if task.due is not None
            and not task.is_planned_this_week
            and (task.due - now).days <= self._horizon_days
        ]
        return render_task_list_section(
            DUE_WITHOUT_WEEKLY_PLAN_TITLE % self._horizon_days,
            unplanned
        )
