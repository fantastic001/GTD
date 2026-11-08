from typing import List

from gtd.extraction.extractor import Extractor, ExtractorFactory
from gtd.report.extractors.project_closure_dates import (
    ProjectClosureDatesExtractor,
)


class ProjectDataExtractorFactory(ExtractorFactory):

    def create_extractors(self) -> List[Extractor]:
        return [ProjectClosureDatesExtractor()]
