import html
from typing import List, Sequence

from gtd.context_keys import ContextKey, ReportSectionKey
from gtd.domain import ActionPointSuggestion
from gtd.extraction.extractor import Context
from gtd.report.rendering import group_by, subsection
from gtd.report.section_extractor import ReportSectionExtractor
from gtd.style import items, paragraph, section, task_reference

ACTION_POINTS_TITLE = "Tasks this week without checklist"
NO_SUGGESTIONS_MESSAGE = "No suggestions found"


def render_suggestion(suggestion: ActionPointSuggestion) -> List[str]:
    reference = paragraph(task_reference(suggestion.task))
    if suggestion.action_points:
        escaped = [html.escape(point) for point in suggestion.action_points]
        return [reference, items(escaped)]
    else:
        return [reference, paragraph(NO_SUGGESTIONS_MESSAGE)]


def render_project_suggestions(
    project: str,
    suggestions: Sequence[ActionPointSuggestion]
) -> List[str]:
    elements = [subsection(project)]
    for suggestion in suggestions:
        elements += render_suggestion(suggestion)
    return elements


class ActionPointsSectionExtractor(ReportSectionExtractor):

    def section_key(self) -> str:
        return ReportSectionKey.ACTION_POINTS

    def dependencies(self) -> List[str]:
        return [ContextKey.SUGGESTED_ACTION_POINTS]

    def render_section(self, context: Context) -> List[str]:
        by_project = group_by(
            context[ContextKey.SUGGESTED_ACTION_POINTS],
            lambda suggestion: suggestion.task.project
        )
        elements = [section(ACTION_POINTS_TITLE)]
        for project, suggestions in by_project.items():
            elements += render_project_suggestions(project, suggestions)
        return elements
