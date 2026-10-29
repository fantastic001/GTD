import logging
from typing import Any, Callable, List

from gtd.context_keys import ContextKey
from gtd.domain import ActionPointSuggestion, Task
from gtd.extraction.extractor import Context, Extractor
from gtd.trello.task_mapping import TRELLO_SOURCE

logger = logging.getLogger(__name__)

ACTION_POINTS_CHECKLIST_NAME = "Checklist"
ACTION_POINT_INSTRUCTIONS = (
    "Action points should be doable in 30 minutes each.\n"
    "Please provide a list of at most 7 action points.\n"
)

ActionPointsAdvisor = Callable[[str, Any], List[str]]
CredentialsLoader = Callable[[], Any]
ProjectContextReader = Callable[[str], str]


class TrelloActionPointsExtractor(Extractor):

    def __init__(
        self,
        api,
        suggest_action_points: ActionPointsAdvisor,
        load_credentials: CredentialsLoader,
        read_project_context: ProjectContextReader
    ) -> None:
        self._api = api
        self._suggest_action_points = suggest_action_points
        self._load_credentials = load_credentials
        self._read_project_context = read_project_context

    def dependencies(self) -> List[str]:
        return [ContextKey.OPEN_TASKS]

    def output(self) -> List[str]:
        return [ContextKey.SUGGESTED_ACTION_POINTS]

    def extract(self, context: Context) -> Context:
        tasks = [
            task for task in context[ContextKey.OPEN_TASKS]
            if task.source == TRELLO_SOURCE
            and task.is_planned_this_week
            and not task.has_checklist
        ]
        if tasks:
            credentials = self._load_credentials()
            suggestions = [self._suggest(task, credentials) for task in tasks]
            return {ContextKey.SUGGESTED_ACTION_POINTS: suggestions}
        else:
            return {ContextKey.SUGGESTED_ACTION_POINTS: []}

    def _describe(self, task: Task) -> str:
        return (
            "Title: %s\nDescription: %s\nProject: %s\nContext: %s\n%s"
            % (
                task.title,
                task.description,
                task.project,
                self._read_project_context(task.project),
                ACTION_POINT_INSTRUCTIONS,
            )
        )

    def _suggest(self, task: Task, credentials: Any) -> ActionPointSuggestion:
        action_points = list(
            self._suggest_action_points(self._describe(task), credentials)
        )
        logger.info(
            "Suggested action points for %s: %s",
            task.title,
            action_points
        )
        if action_points:
            self._store_as_checklist(task, action_points)
        else:
            logger.info("No action points suggested for %s", task.title)
        return ActionPointSuggestion(task, tuple(action_points))

    def _store_as_checklist(self, task: Task, action_points: List[str]) -> None:
        checklist = self._api.add_checklist(
            task.identifier,
            ACTION_POINTS_CHECKLIST_NAME
        )
        for action_point in action_points:
            self._api.add_checklist_item(checklist["id"], action_point)
