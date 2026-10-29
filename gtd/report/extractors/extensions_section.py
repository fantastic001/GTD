from typing import Callable, List

from gtd.context_keys import ReportSectionKey
from gtd.extraction.extractor import Context
from gtd.report.section_extractor import ReportSectionExtractor

ExtensionsLoader = Callable[[], List[str]]


class ExtensionsSectionExtractor(ReportSectionExtractor):

    def __init__(self, load_extensions: ExtensionsLoader) -> None:
        self._load_extensions = load_extensions

    def section_key(self) -> str:
        return ReportSectionKey.EXTENSIONS

    def dependencies(self) -> List[str]:
        return []

    def render_section(self, context: Context) -> List[str]:
        return list(self._load_extensions())
