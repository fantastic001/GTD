import datetime
from typing import Callable, List

from gtd.context_keys import ContextKey
from gtd.extraction.extractor import Context, Extractor

Clock = Callable[[], datetime.datetime]


class CalendarExtractor(Extractor):

    def __init__(self, clock: Clock = datetime.datetime.now) -> None:
        self._clock = clock

    def dependencies(self) -> List[str]:
        return []

    def output(self) -> List[str]:
        return [ContextKey.NOW, ContextKey.WEEK_START]

    def extract(self, context: Context) -> Context:
        now = self._clock()
        week_start = (now - datetime.timedelta(days=now.weekday())).date()
        return {ContextKey.NOW: now, ContextKey.WEEK_START: week_start}
