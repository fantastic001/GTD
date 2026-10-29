from abc import ABC, abstractmethod
from typing import Any, Dict, List

Context = Dict[str, Any]


class Extractor(ABC):

    @abstractmethod
    def dependencies(self) -> List[str]:
        ...

    @abstractmethod
    def output(self) -> List[str]:
        ...

    @abstractmethod
    def extract(self, context: Context) -> Context:
        ...

    def name(self) -> str:
        return type(self).__name__


class ExtractorFactory(ABC):

    @abstractmethod
    def create_extractors(self) -> List[Extractor]:
        ...
