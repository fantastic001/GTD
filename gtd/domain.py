import datetime
from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass(frozen=True)
class Project:
    name: str
    context: str


@dataclass(frozen=True)
class Task:
    source: str
    identifier: str
    title: str
    description: str
    url: str
    reference: str
    project: str
    context: str
    labels: Tuple[str, ...]
    due: Optional[datetime.datetime]
    created: Optional[datetime.datetime]
    last_activity: Optional[datetime.date]
    closed_on: Optional[datetime.date]
    is_closed: bool
    is_planned_this_week: bool
    has_checklist: bool


@dataclass(frozen=True)
class Deliverable:
    task: Task
    attachment_urls: Tuple[str, ...]
    comments: Tuple[str, ...]


@dataclass(frozen=True)
class ActionPointSuggestion:
    task: Task
    action_points: Tuple[str, ...]
