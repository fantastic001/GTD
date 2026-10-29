from abc import abstractmethod
from typing import List

from gtd.extraction.extractor import Context, Extractor


class ReportSectionExtractor(Extractor):

    @abstractmethod
    def section_key(self) -> str:
        ...

    @abstractmethod
    def render_section(self, context: Context) -> List[str]:
        ...

    def output(self) -> List[str]:
        return [self.section_key()]

    def extract(self, context: Context) -> Context:
        return {self.section_key(): self.render_section(context)}
