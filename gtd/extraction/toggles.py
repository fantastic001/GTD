from abc import ABC, abstractmethod
from typing import Callable, List, Sequence, Tuple

from gtd.config import get_config_bool
from gtd.extraction.extractor import Extractor

ExtractorBuilder = Callable[[], Extractor]


class FeatureToggle(ABC):

    @abstractmethod
    def is_enabled(self) -> bool:
        ...


class AlwaysEnabled(FeatureToggle):

    def is_enabled(self) -> bool:
        return True


class ConfigFlag(FeatureToggle):

    def __init__(self, key: str, default: bool, doc: str) -> None:
        self._key = key
        self._default = default
        self._doc = doc

    def is_enabled(self) -> bool:
        return get_config_bool(self._key, self._default, self._doc)


class Inverted(FeatureToggle):

    def __init__(self, toggle: FeatureToggle) -> None:
        self._toggle = toggle

    def is_enabled(self) -> bool:
        return not self._toggle.is_enabled()


class AvailabilityToggle(FeatureToggle):

    def __init__(self, is_available: Callable[[], bool]) -> None:
        self._is_available = is_available

    def is_enabled(self) -> bool:
        return self._is_available()


ToggledExtractor = Tuple[FeatureToggle, ExtractorBuilder]


def create_enabled_extractors(
    toggled_extractors: Sequence[ToggledExtractor]
) -> List[Extractor]:
    return [
        build_extractor()
        for toggle, build_extractor in toggled_extractors
        if toggle.is_enabled()
    ]
