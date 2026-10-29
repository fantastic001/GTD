import html
from collections import Counter
from typing import Dict, List, Sequence

from gtd.context_keys import ContextKey, ReportSectionKey
from gtd.domain import Project, Task
from gtd.extraction.extractor import Context
from gtd.report.section_extractor import ReportSectionExtractor
from gtd.style import section, table

PER_PROJECT_TITLE = "Number of open tasks per project"
PER_CONTEXT_TITLE = "Number of open tasks per context"
PROJECT_COLUMN = "Project"
CONTEXT_COLUMN = "Context"
COUNT_COLUMN = "Number of open tasks"
CUMULATIVE_COLUMN = "Cumulative"


def tabulate_open_tasks_per_project(
    projects: Sequence[Project],
    open_tasks: Sequence[Task]
) -> List[Dict[str, object]]:
    counts = Counter((task.context, task.project) for task in open_tasks)
    records: List[Dict[str, object]] = []
    cumulative = 0
    for project in projects:
        count = counts[(project.context, project.name)]
        cumulative += count
        records.append({
            PROJECT_COLUMN: html.escape(project.name),
            COUNT_COLUMN: count,
            CUMULATIVE_COLUMN: cumulative,
        })
    return records


def tabulate_open_tasks_per_context(
    contexts: Sequence[str],
    open_tasks: Sequence[Task]
) -> List[Dict[str, object]]:
    counts = Counter(task.context for task in open_tasks)
    return [
        {CONTEXT_COLUMN: html.escape(context), COUNT_COLUMN: counts[context]}
        for context in contexts
        if counts[context] > 0
    ]


class OpenTasksDistributionSectionExtractor(ReportSectionExtractor):

    def section_key(self) -> str:
        return ReportSectionKey.OPEN_TASKS_DISTRIBUTION

    def dependencies(self) -> List[str]:
        return [ContextKey.OPEN_TASKS, ContextKey.PROJECTS, ContextKey.CONTEXTS]

    def render_section(self, context: Context) -> List[str]:
        open_tasks = context[ContextKey.OPEN_TASKS]
        contexts = context[ContextKey.CONTEXTS]
        if len(contexts) == 1:
            records = tabulate_open_tasks_per_project(
                context[ContextKey.PROJECTS],
                open_tasks
            )
            return [section(PER_PROJECT_TITLE), table(records)]
        else:
            records = tabulate_open_tasks_per_context(contexts, open_tasks)
            return [section(PER_CONTEXT_TITLE), table(records)]
