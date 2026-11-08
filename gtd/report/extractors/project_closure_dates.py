import datetime
from typing import Dict, List

from gtd.context_keys import ContextKey
from gtd.domain import Project, Task
from gtd.extraction.extractor import Context, Extractor
from gtd.report.rendering import group_by


def project_of(task: Task) -> Project:
    return Project(name=task.project, context=task.context)


class ProjectClosureDatesExtractor(Extractor):

    def dependencies(self) -> List[str]:
        return [ContextKey.CLOSED_TASKS, ContextKey.CLOSED_PROJECTS]

    def output(self) -> List[str]:
        return [ContextKey.PROJECT_CLOSURE_DATES]

    def extract(self, context: Context) -> Context:
        closed_projects = set(context[ContextKey.CLOSED_PROJECTS])
        dated_tasks_per_project = group_by(
            [t for t in context[ContextKey.CLOSED_TASKS] if t.closed_on],
            project_of
        )
        closure_dates: Dict[Project, datetime.date] = {
            project: max(task.closed_on for task in tasks)
            for project, tasks in dated_tasks_per_project.items()
            if project in closed_projects
        }
        return {ContextKey.PROJECT_CLOSURE_DATES: closure_dates}
