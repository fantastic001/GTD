import datetime
from typing import Dict, List, Optional, Sequence, Set

from gtd.context_keys import ContextKey
from gtd.domain import Project, ProjectProgress, ProjectStatus, Task
from gtd.extraction.extractor import Context, Extractor
from gtd.report.month import is_in_month
from gtd.report.rendering import group_by

STATUS_ORDER = [ProjectStatus.DONE, ProjectStatus.IN_PROGRESS]


def project_of(task: Task) -> Project:
    return Project(name=task.project, context=task.context)


def classify_project(
    closed_on: Optional[datetime.date],
    tasks_done_in_month: int,
    month: datetime.date
) -> Optional[ProjectStatus]:
    if is_in_month(closed_on, month):
        return ProjectStatus.DONE
    elif tasks_done_in_month > 0:
        return ProjectStatus.IN_PROGRESS
    else:
        return None


class ProjectProgressAssessor:

    def __init__(
        self,
        closed_projects: Set[Project],
        month: datetime.date
    ) -> None:
        self._closed_projects = closed_projects
        self._month = month

    def assess(
        self,
        project: Project,
        tasks: Sequence[Task]
    ) -> Optional[ProjectProgress]:
        closed_on = self._estimate_project_closure(project, tasks)
        done_in_month = len([
            task for task in tasks if is_in_month(task.closed_on, self._month)
        ])
        status = classify_project(closed_on, done_in_month, self._month)
        if status is not None:
            return ProjectProgress(project, status, done_in_month, closed_on)
        else:
            return None

    def _estimate_project_closure(
        self,
        project: Project,
        tasks: Sequence[Task]
    ) -> Optional[datetime.date]:
        if project in self._closed_projects:
            return max(task.closed_on for task in tasks)
        else:
            return None


class MonthlyProjectProgressExtractor(Extractor):

    def dependencies(self) -> List[str]:
        return [
            ContextKey.CLOSED_TASKS,
            ContextKey.CLOSED_PROJECTS,
            ContextKey.REPORT_MONTH,
        ]

    def output(self) -> List[str]:
        return [ContextKey.MONTHLY_PROJECT_PROGRESS]

    def extract(self, context: Context) -> Context:
        month = context[ContextKey.REPORT_MONTH]
        if isinstance(month, datetime.date):
            assessor = ProjectProgressAssessor(
                set(context[ContextKey.CLOSED_PROJECTS]),
                month
            )
        else:
            raise TypeError("Report month must be a date, got %r" % month)
        tasks_per_project: Dict[Project, List[Task]] = group_by(
            [t for t in context[ContextKey.CLOSED_TASKS] if t.closed_on],
            project_of
        )
        assessed = [
            assessor.assess(project, tasks)
            for project, tasks in tasks_per_project.items()
        ]
        progress = [p for p in assessed if p is not None]
        return {
            ContextKey.MONTHLY_PROJECT_PROGRESS: sorted(
                progress,
                key=lambda p: (STATUS_ORDER.index(p.status), p.project.name)
            )
        }
