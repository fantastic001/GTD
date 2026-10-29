import datetime
from typing import List, Sequence

from gtd.context_keys import ContextKey, ReportSectionKey
from gtd.domain import Task
from gtd.extraction.extractor import Context
from gtd.report.section_extractor import ReportSectionExtractor
from gtd.style import paragraph, section

STATISTICS_TITLE = "Statistics"
NO_CLOSED_TASKS_MESSAGE = (
    "No tasks closed yet. Please close some tasks to see statistics."
)
DATE_FORMAT = "%Y-%m-%d"


def count_days_since_first_activity(
    tasks: Sequence[Task],
    today: datetime.date
) -> int:
    activity_days = [t.last_activity for t in tasks if t.last_activity]
    first_day = min(activity_days, default=today)
    return max(1, 1 + (today - first_day).days)


def count_remaining_days_in_year(today: datetime.date) -> int:
    return 1 + (datetime.date(today.year, 12, 31) - today).days


def projected_completion(
    today: datetime.date,
    open_count: int,
    daily_rate: float
) -> str:
    days_needed = datetime.timedelta(days=open_count / daily_rate)
    return (today + days_needed).strftime(DATE_FORMAT)


class ClosureStatistics:

    def __init__(self, context: Context) -> None:
        self._open_tasks = context[ContextKey.OPEN_TASKS]
        self._closed_tasks = context[ContextKey.CLOSED_TASKS]
        self._closed_this_week = context[ContextKey.CLOSED_THIS_WEEK_TASKS]
        self._today = context[ContextKey.NOW].date()
        self._week_start = context[ContextKey.WEEK_START]

    def render(self) -> List[str]:
        open_count = len(self._open_tasks)
        daily_rate = len(self._closed_tasks) / count_days_since_first_activity(
            list(self._open_tasks) + list(self._closed_tasks),
            self._today
        )
        remaining_days = count_remaining_days_in_year(self._today)
        return [
            "Average tasks closed per day: %.2f" % daily_rate,
            "Remaining days in year: %d" % remaining_days,
            "Required closed tasks per day: %.2f"
            % (open_count / remaining_days),
            "Start of week: %s" % self._week_start,
            "If you continue with this closing rate, all tasks will be "
            "closed by %s"
            % projected_completion(self._today, open_count, daily_rate),
            "If you continue with closing rate 1 per day, all tasks will be "
            "closed by %s" % projected_completion(self._today, open_count, 1),
        ] + self._render_weekly_balance()

    def _render_weekly_balance(self) -> List[str]:
        opened_count = len([
            task for task in self._open_tasks
            if task.created is not None
            and task.created.date() >= self._week_start
        ])
        closed_count = len(self._closed_this_week)
        return [
            "Tasks opened this week: %d" % opened_count,
            "Net closure this week: %d" % (closed_count - opened_count),
            "Tasks closed this week: %d" % closed_count,
        ]


class StatisticsSectionExtractor(ReportSectionExtractor):

    def section_key(self) -> str:
        return ReportSectionKey.STATISTICS

    def dependencies(self) -> List[str]:
        return [
            ContextKey.OPEN_TASKS,
            ContextKey.CLOSED_TASKS,
            ContextKey.CLOSED_THIS_WEEK_TASKS,
            ContextKey.NOW,
            ContextKey.WEEK_START,
        ]

    def render_section(self, context: Context) -> List[str]:
        open_count = len(context[ContextKey.OPEN_TASKS])
        header = [
            section(STATISTICS_TITLE),
            paragraph("Number of open tasks: %d" % open_count),
        ]
        if context[ContextKey.CLOSED_TASKS]:
            lines = ClosureStatistics(context).render()
            return header + [paragraph(line) for line in lines]
        else:
            return header + [paragraph(NO_CLOSED_TASKS_MESSAGE)]
