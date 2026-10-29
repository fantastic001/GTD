import html
from typing import Callable, Dict, Iterable, List, Sequence, TypeVar

from gtd.domain import Task
from gtd.style import items, section, task_reference

Element = TypeVar("Element")
GroupKey = TypeVar("GroupKey")


def group_by(
    elements: Iterable[Element],
    key: Callable[[Element], GroupKey]
) -> Dict[GroupKey, List[Element]]:
    groups: Dict[GroupKey, List[Element]] = {}
    for element in elements:
        groups.setdefault(key(element), []).append(element)
    return groups


def subsection(title: str) -> str:
    return section(html.escape(title), level=1)


def task_items(tasks: Sequence[Task]) -> str:
    return items([task_reference(task) for task in tasks])


def render_task_list_section(title: str, tasks: Sequence[Task]) -> List[str]:
    if tasks:
        return [section(title), task_items(tasks)]
    else:
        return []


def render_tasks_grouped_by_project(
    title: str,
    tasks: Sequence[Task]
) -> List[str]:
    elements = [section(title)]
    for project, project_tasks in group_by(tasks, lambda t: t.project).items():
        elements += [subsection(project), task_items(project_tasks)]
    return elements
