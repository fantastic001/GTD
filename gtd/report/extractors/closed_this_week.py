from typing import List

from gtd.context_keys import ContextKey
from gtd.extraction.extractor import Context, Extractor


class ClosedThisWeekExtractor(Extractor):

    def dependencies(self) -> List[str]:
        return [ContextKey.CLOSED_TASKS, ContextKey.WEEK_START]

    def output(self) -> List[str]:
        return [ContextKey.CLOSED_THIS_WEEK_TASKS]

    def extract(self, context: Context) -> Context:
        week_start = context[ContextKey.WEEK_START]
        return {
            ContextKey.CLOSED_THIS_WEEK_TASKS: [
                task for task in context[ContextKey.CLOSED_TASKS]
                if task.closed_on is not None and task.closed_on >= week_start
            ]
        }
