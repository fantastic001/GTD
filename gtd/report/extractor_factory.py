from typing import List, Sequence

from gtd.config import get_config_int, get_config_str
from gtd.extensions import load_extensions
from gtd.extraction.extractor import Extractor, ExtractorFactory
from gtd.extraction.toggles import (
    ConfigFlag,
    Inverted,
    ToggledExtractor,
    create_enabled_extractors,
)
from gtd.report.extractors.action_points_section import (
    ActionPointsSectionExtractor,
)
from gtd.report.extractors.calendar import CalendarExtractor
from gtd.report.extractors.closed_this_week import ClosedThisWeekExtractor
from gtd.report.extractors.closed_this_week_section import (
    ClosedThisWeekSectionExtractor,
)
from gtd.report.extractors.deliverables_section import (
    DeliverablesSectionExtractor,
)
from gtd.report.extractors.due_soon_without_checklist_section import (
    DueSoonWithoutChecklistSectionExtractor,
)
from gtd.report.extractors.due_without_weekly_plan_section import (
    DueWithoutWeeklyPlanSectionExtractor,
)
from gtd.report.extractors.extensions_section import (
    ExtensionsSectionExtractor,
)
from gtd.report.extractors.open_tasks_distribution_section import (
    OpenTasksDistributionSectionExtractor,
)
from gtd.report.extractors.report import ReportExtractor
from gtd.report.extractors.statistics_section import (
    StatisticsSectionExtractor,
)
from gtd.report.extractors.this_week_with_checklist_section import (
    ThisWeekWithChecklistSectionExtractor,
)
from gtd.report.extractors.weekly_score_section import (
    WeeklyScoreSectionExtractor,
)

DEFAULT_REPORT_TITLE = "GTD Report"
DEFAULT_DUE_SOON_DAYS = 7
DEFAULT_DUE_WITHOUT_PLAN_DAYS = 14

DELIVERABLES_FLAG = ConfigFlag(
    "report_deliverables",
    True,
    "Whether to report deliverables instead of closed tasks this week"
)


def section_flag(name: str) -> ConfigFlag:
    return ConfigFlag(
        "report_show_" + name,
        True,
        "Whether to include the %s section in the report" % name
    )


class ReportExtractorFactory(ExtractorFactory):

    def create_extractors(self) -> List[Extractor]:
        sections = create_enabled_extractors(self._section_table())
        title = get_config_str(
            "report_title",
            DEFAULT_REPORT_TITLE,
            "Title of the generated report"
        )
        return [
            CalendarExtractor(),
            ClosedThisWeekExtractor(),
            *sections,
            ReportExtractor(title, self._section_keys(sections)),
        ]

    def _section_keys(self, sections: Sequence[Extractor]) -> List[str]:
        return [key for extractor in sections for key in extractor.output()]

    def _section_table(self) -> List[ToggledExtractor]:
        due_soon_days = get_config_int(
            "report_due_soon_days",
            DEFAULT_DUE_SOON_DAYS,
            "Horizon in days for due tasks without checklist"
        )
        due_without_plan_days = get_config_int(
            "report_due_without_plan_days",
            DEFAULT_DUE_WITHOUT_PLAN_DAYS,
            "Horizon in days for due tasks not planned for this week"
        )
        return [
            (
                section_flag("this_week_with_checklist"),
                ThisWeekWithChecklistSectionExtractor
            ),
            (
                section_flag("due_soon_without_checklist"),
                lambda: DueSoonWithoutChecklistSectionExtractor(due_soon_days)
            ),
            (
                section_flag("due_without_weekly_plan"),
                lambda: DueWithoutWeeklyPlanSectionExtractor(
                    due_without_plan_days
                )
            ),
            (
                ConfigFlag(
                    "report_this_week_without_checklist",
                    False,
                    "Whether to suggest action points for tasks this week "
                    "without checklist"
                ),
                ActionPointsSectionExtractor
            ),
            (
                section_flag("open_tasks_distribution"),
                OpenTasksDistributionSectionExtractor
            ),
            (section_flag("statistics"), StatisticsSectionExtractor),
            (
                ConfigFlag(
                    "report_score",
                    False,
                    "Whether to report score for closed tasks this week"
                ),
                WeeklyScoreSectionExtractor
            ),
            (Inverted(DELIVERABLES_FLAG), ClosedThisWeekSectionExtractor),
            (DELIVERABLES_FLAG, DeliverablesSectionExtractor),
            (
                section_flag("extensions"),
                lambda: ExtensionsSectionExtractor(load_extensions)
            ),
        ]
