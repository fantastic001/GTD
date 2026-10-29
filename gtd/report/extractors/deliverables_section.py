import html
import re
from typing import List, Sequence

from gtd.context_keys import ContextKey, ReportSectionKey
from gtd.domain import Deliverable
from gtd.extraction.extractor import Context
from gtd.report.rendering import group_by, subsection
from gtd.report.section_extractor import ReportSectionExtractor
from gtd.style import items, paragraph, red, section, task_reference

DELIVERABLES_TITLE = "Deliverables this week for %s"
MISSING_DELIVERABLES_MESSAGE = (
    "Without deliverables %s - please add a comment with a link to the "
    "deliverable or attach the deliverable to the task"
)
URL_PATTERN = re.compile(r"https?://\S+")
LINK_SUBSTITUTIONS = [
    (re.compile(r"\[([^\]]+)\]\((https?://\S+)\)"), r'<a href="\2">\1</a>'),
    (
        re.compile(r"\[([^\]]+)\]\((https?://\S+) [^\)]*\)"),
        r'<a href="\2">\1</a>'
    ),
    (re.compile(r"([ \t\n])(https?://\S+)"), r'\1<a href="\2">\2</a>'),
    (re.compile(r"^(https?://\S+)"), r'<a href="\1">\1</a>'),
]


def linkify(text: str) -> str:
    escaped = html.escape(text, quote=True)
    if URL_PATTERN.search(escaped):
        for pattern, replacement in LINK_SUBSTITUTIONS:
            escaped = pattern.sub(replacement, escaped)
        return escaped
    else:
        return escaped


def describe_deliverable(deliverable: Deliverable) -> List[str]:
    title = html.escape(deliverable.task.title)
    attachments = [
        "%s: %s" % (title, html.escape(url))
        for url in deliverable.attachment_urls
    ]
    comments = [
        "%s: %s" % (title, linkify(comment))
        for comment in deliverable.comments
    ]
    return attachments + comments


def has_no_evidence(deliverable: Deliverable) -> bool:
    return not deliverable.attachment_urls and not deliverable.comments


def render_context_deliverables(
    context_name: str,
    deliverables: Sequence[Deliverable]
) -> List[str]:
    elements = [section(DELIVERABLES_TITLE % html.escape(context_name))]
    elements += [
        paragraph(red(MISSING_DELIVERABLES_MESSAGE % task_reference(d.task)))
        for d in deliverables
        if has_no_evidence(d) and d.task.is_closed
    ]
    by_project = group_by(deliverables, lambda d: d.task.project)
    for project, project_deliverables in by_project.items():
        entries = [
            entry
            for deliverable in project_deliverables
            for entry in describe_deliverable(deliverable)
        ]
        if entries:
            elements += [subsection(project), items(entries)]
        else:
            continue
    return elements


class DeliverablesSectionExtractor(ReportSectionExtractor):

    def section_key(self) -> str:
        return ReportSectionKey.DELIVERABLES

    def dependencies(self) -> List[str]:
        return [ContextKey.DELIVERABLES]

    def render_section(self, context: Context) -> List[str]:
        by_context = group_by(
            context[ContextKey.DELIVERABLES],
            lambda deliverable: deliverable.task.context
        )
        elements: List[str] = []
        for context_name, deliverables in by_context.items():
            elements += render_context_deliverables(context_name, deliverables)
        return elements
