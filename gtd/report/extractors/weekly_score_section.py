from typing import List

from gtd.context_keys import ContextKey, ReportSectionKey
from gtd.extraction.extractor import Context
from gtd.report.section_extractor import ReportSectionExtractor
from gtd.style import paragraph


class WeeklyScoreSectionExtractor(ReportSectionExtractor):

    def section_key(self) -> str:
        return ReportSectionKey.WEEKLY_SCORE

    def dependencies(self) -> List[str]:
        return [ContextKey.WEEKLY_SCORE]

    def render_section(self, context: Context) -> List[str]:
        score = context[ContextKey.WEEKLY_SCORE]
        return [paragraph("Score for this week: %d" % score)]
