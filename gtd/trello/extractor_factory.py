import logging
from typing import List

import gtd.trello as trello_plugin
from gtd.config import get_config_str
from gtd.drive import get_context_for_project
from gtd.extraction.extractor import Extractor, ExtractorFactory
from gtd.extraction.toggles import (
    AvailabilityToggle,
    ConfigFlag,
    ToggledExtractor,
    create_enabled_extractors,
)
from gtd.trello.extractors.action_points import TrelloActionPointsExtractor
from gtd.trello.extractors.ai_help import TrelloAiHelpExtractor
from gtd.trello.extractors.boards import TrelloBoardsExtractor
from gtd.trello.extractors.closed_cards import TrelloClosedCardsExtractor
from gtd.trello.extractors.closed_lists import TrelloClosedListExtractor
from gtd.trello.extractors.closed_tasks import TrelloClosedTasksExtractor
from gtd.trello.extractors.closure_dates import TrelloClosureDatesExtractor
from gtd.trello.extractors.deliverables import TrelloDeliverablesExtractor
from gtd.trello.extractors.lists import TrelloListExtractor
from gtd.trello.extractors.open_cards import TrelloOpenCardsExtractor
from gtd.trello.extractors.open_tasks import TrelloOpenTasksExtractor
from gtd.trello.extractors.score import TrelloScoreExtractor

logger = logging.getLogger(__name__)

DEFAULT_THIS_WEEK_LABEL = "This week"
DEFAULT_PRIMARY_LABEL = "Primary"
DEFAULT_AI_HELP_LABEL = "Help"


class TrelloSettings:

    def __init__(self) -> None:
        self.apikey = get_config_str("trello_apikey", "", "Trello API key")
        self.token = get_config_str("trello_token", "", "Trello token")
        self.this_week_label = get_config_str(
            "trello_this_week_label",
            DEFAULT_THIS_WEEK_LABEL,
            "Label Used in tasks in Trello to mark tasks for this week"
        )
        self.primary_label = get_config_str(
            "trello_primary_label",
            DEFAULT_PRIMARY_LABEL,
            "Label used in Trello to mark primary tasks"
        )
        self.ai_help_label = get_config_str(
            "trello_ai_help_label",
            DEFAULT_AI_HELP_LABEL,
            "Label Used in tasks in Trello to mark tasks for AI help"
        )


class TrelloExtractorFactory(ExtractorFactory):

    def create_extractors(self) -> List[Extractor]:
        settings = TrelloSettings()
        api = trello_plugin.TrelloAPI(
            apikey=settings.apikey,
            token=settings.token
        )
        board_names = api.get_default_boards()
        logger.info("Creating Trello extractors for boards %s", board_names)
        return self._create_data_extractors(
            api,
            board_names,
            settings
        ) + create_enabled_extractors(self._optional_table(api, settings))

    def _create_data_extractors(
        self,
        api,
        board_names: List[str],
        settings: TrelloSettings
    ) -> List[Extractor]:
        return [
            TrelloBoardsExtractor(api, board_names),
            TrelloListExtractor(api, board_names),
            TrelloClosedListExtractor(api, board_names),
            TrelloOpenCardsExtractor(api, board_names),
            TrelloClosedCardsExtractor(api, board_names),
            TrelloClosureDatesExtractor(api),
            TrelloOpenTasksExtractor(api, settings.this_week_label),
            TrelloClosedTasksExtractor(api, settings.this_week_label),
        ]

    def _optional_table(
        self,
        api,
        settings: TrelloSettings
    ) -> List[ToggledExtractor]:
        return [
            (
                ConfigFlag(
                    "report_deliverables",
                    True,
                    "Whether to report deliverables for tasks this week"
                ),
                lambda: TrelloDeliverablesExtractor(api, settings.primary_label)
            ),
            (
                ConfigFlag(
                    "report_score",
                    False,
                    "Whether to report score for closed tasks this week"
                ),
                lambda: TrelloScoreExtractor(api)
            ),
            (
                ConfigFlag(
                    "report_this_week_without_checklist",
                    False,
                    "Whether to suggest action points for tasks this week "
                    "without checklist"
                ),
                lambda: TrelloActionPointsExtractor(
                    api,
                    trello_plugin.get_action_points,
                    trello_plugin.load_credentials,
                    get_context_for_project
                )
            ),
            (
                AvailabilityToggle(lambda: trello_plugin.ai_enabled),
                lambda: TrelloAiHelpExtractor(
                    api,
                    settings.ai_help_label,
                    trello_plugin.ai_help
                )
            ),
        ]
