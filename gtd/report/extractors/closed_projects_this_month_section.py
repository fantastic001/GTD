import datetime
import html
from typing import List, Mapping

from gtd.context_keys import ContextKey, ReportSectionKey
from gtd.domain import Project
from gtd.extraction.extractor import Context
from gtd.report.month import is_in_month
from gtd.report.rendering import group_by, subsection
from gtd.report.section_extractor import ReportSectionExtractor
from gtd.style import items, paragraph, section

CLOSED_PROJECTS_THIS_MONTH_TITLE = "Projects closed this month"
NO_CLOSED_PROJECTS_MESSAGE = "No projects closed this month"
CLOSED_PROJECT_ENTRY = "%s (closed on %s)"


def select_projects_closed_in_month(
    closure_dates: Mapping[Project, datetime.date],
    month: datetime.date
) -> List[Project]:
    closed_in_month = [
        project
        for project, closed_on in closure_dates.items()
        if is_in_month(closed_on, month)
    ]
    return sorted(closed_in_month, key=lambda p: (closure_dates[p], p.name))


class ClosedProjectsThisMonthSectionExtractor(ReportSectionExtractor):

    def section_key(self) -> str:
        return ReportSectionKey.CLOSED_PROJECTS_THIS_MONTH

    def dependencies(self) -> List[str]:
        return [ContextKey.PROJECT_CLOSURE_DATES, ContextKey.NOW]

    def render_section(self, context: Context) -> List[str]:
        closure_dates = context[ContextKey.PROJECT_CLOSURE_DATES]
        closed_projects = select_projects_closed_in_month(
            closure_dates,
            context[ContextKey.NOW].date()
        )
        elements = [section(CLOSED_PROJECTS_THIS_MONTH_TITLE)]
        if closed_projects:
            by_context = group_by(closed_projects, lambda p: p.context)
            for context_name, projects in by_context.items():
                elements += [
                    subsection(context_name),
                    items([
                        CLOSED_PROJECT_ENTRY % (
                            html.escape(p.name),
                            closure_dates[p].isoformat()
                        )
                        for p in projects
                    ]),
                ]
            return elements
        else:
            return elements + [paragraph(NO_CLOSED_PROJECTS_MESSAGE)]
