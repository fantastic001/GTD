from typing import List

from gtd.config import get_config_str
from gtd.context_keys import ContextKey
from gtd.extraction.extractor import Extractor, ExtractorFactory
from gtd.extraction.toggles import (
    ConfigFlag,
    ToggledExtractor,
    create_enabled_extractors,
)
from gtd.report.extractors.monthly_project_progress import (
    MonthlyProjectProgressExtractor,
)
from gtd.report.extractors.monthly_projects_section import (
    MonthlyProjectsSectionExtractor,
)
from gtd.report.extractors.report import ReportExtractor

DEFAULT_MONTHLY_REPORT_TITLE = "GTD Monthly Project Report"


def monthly_section_flag(name: str) -> ConfigFlag:
    return ConfigFlag(
        "monthly_report_show_" + name,
        True,
        "Whether to include the %s section in the monthly report" % name
    )


class MonthlyReportExtractorFactory(ExtractorFactory):

    def create_extractors(self) -> List[Extractor]:
        sections = create_enabled_extractors(self._section_table())
        title = get_config_str(
            "monthly_report_title",
            DEFAULT_MONTHLY_REPORT_TITLE,
            "Title of the generated monthly report"
        )
        return [
            MonthlyProjectProgressExtractor(),
            *sections,
            ReportExtractor(
                title,
                [key for extractor in sections for key in extractor.output()],
                ContextKey.MONTHLY_REPORT
            ),
        ]

    def _section_table(self) -> List[ToggledExtractor]:
        return [
            (monthly_section_flag("projects"), MonthlyProjectsSectionExtractor),
        ]
