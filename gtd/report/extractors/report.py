import html
from typing import List, Sequence

from gtd.context_keys import ContextKey
from gtd.extraction.extractor import Context, Extractor
from gtd.style import section

DOCUMENT_HEAD = [
    "<!DOCTYPE html>",
    "<html>",
    "<head>",
    "<meta charset='utf-8'>",
    "</head>",
    "<body>",
]
DOCUMENT_TAIL = ["</body>", "</html>"]


class ReportExtractor(Extractor):

    def __init__(self, title: str, section_keys: Sequence[str]) -> None:
        if len(set(section_keys)) != len(section_keys):
            raise ValueError("Duplicate report sections: %s" % section_keys)
        self._title = title
        self._section_keys = list(section_keys)

    def dependencies(self) -> List[str]:
        return list(self._section_keys)

    def output(self) -> List[str]:
        return [ContextKey.REPORT]

    def extract(self, context: Context) -> Context:
        body = [
            element
            for key in self._section_keys
            for element in context[key]
        ]
        title = section(html.escape(self._title))
        document = DOCUMENT_HEAD + [title] + body + DOCUMENT_TAIL
        return {ContextKey.REPORT: document}
