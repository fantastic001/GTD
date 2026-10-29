import datetime
import logging
from typing import List, Sequence

from gtd.context_keys import ContextKey
from gtd.domain import Deliverable, Task
from gtd.extraction.extractor import Context, Extractor
from gtd.trello.task_mapping import TRELLO_DATE_FORMAT, TRELLO_SOURCE

logger = logging.getLogger(__name__)


def is_comment_since(comment: dict, week_start: datetime.date) -> bool:
    try:
        written_on = datetime.datetime.strptime(
            comment["date"],
            TRELLO_DATE_FORMAT
        ).date()
    except ValueError:
        logger.warning("Could not parse comment date: %s", comment["date"])
        return False
    return written_on >= week_start


class TrelloDeliverablesExtractor(Extractor):

    def __init__(self, api, primary_label: str) -> None:
        self._api = api
        self._primary_label = primary_label

    def dependencies(self) -> List[str]:
        return [
            ContextKey.OPEN_TASKS,
            ContextKey.CLOSED_THIS_WEEK_TASKS,
            ContextKey.WEEK_START,
        ]

    def output(self) -> List[str]:
        return [ContextKey.DELIVERABLES]

    def extract(self, context: Context) -> Context:
        candidates = self._select_primary_trello_tasks(
            list(context[ContextKey.CLOSED_THIS_WEEK_TASKS])
            + list(context[ContextKey.OPEN_TASKS])
        )
        week_start = context[ContextKey.WEEK_START]
        return {
            ContextKey.DELIVERABLES: [
                self._collect_deliverable(task, week_start)
                for task in candidates
            ]
        }

    def _select_primary_trello_tasks(
        self,
        tasks: Sequence[Task]
    ) -> List[Task]:
        return [
            task for task in tasks
            if task.source == TRELLO_SOURCE
            and self._primary_label in task.labels
        ]

    def _collect_deliverable(
        self,
        task: Task,
        week_start: datetime.date
    ) -> Deliverable:
        card_reference = {"id": task.identifier}
        attachments = self._api.get_attachments(card_reference)
        comments = self._api.get_comments(card_reference)
        return Deliverable(
            task=task,
            attachment_urls=tuple(a["url"] for a in attachments),
            comments=tuple(
                c["text"] for c in comments if is_comment_since(c, week_start)
            ),
        )
