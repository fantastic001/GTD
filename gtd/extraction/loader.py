import importlib
import inspect
import logging
from types import ModuleType
from typing import Iterable, List, Sequence, Type

from gtd.config import get_config_list, load_plugins
from gtd.extraction.errors import ExtractionError
from gtd.extraction.extractor import Extractor, ExtractorFactory

logger = logging.getLogger(__name__)

DEFAULT_BUILTIN_EXTRACTOR_MODULES = ["gtd.report"]


def is_concrete_factory_class(symbol: object) -> bool:
    return (
        inspect.isclass(symbol)
        and issubclass(symbol, ExtractorFactory)
        and not inspect.isabstract(symbol)
    )


def find_factory_classes(
    modules: Iterable[ModuleType]
) -> List[Type[ExtractorFactory]]:
    discovered = [
        symbol
        for module in modules
        for symbol in vars(module).values()
        if is_concrete_factory_class(symbol)
    ]
    return list(dict.fromkeys(discovered))


def load_extractor_modules() -> List[ModuleType]:
    builtin_names = get_config_list(
        "builtin_extractor_modules",
        DEFAULT_BUILTIN_EXTRACTOR_MODULES,
        "Modules providing extractor factories besides configured plugins"
    )
    builtin_modules = [importlib.import_module(n) for n in builtin_names]
    return builtin_modules + [module for _, module in load_plugins()]


def load_extractor_factories() -> List[ExtractorFactory]:
    factory_classes = find_factory_classes(load_extractor_modules())
    logger.info(
        "Discovered extractor factories: %s",
        [factory_class.__name__ for factory_class in factory_classes]
    )
    return [factory_class() for factory_class in factory_classes]


def create_extractors(
    factories: Sequence[ExtractorFactory]
) -> List[Extractor]:
    return [
        extractor
        for factory in factories
        for extractor in create_extractors_of_factory(factory)
    ]


def create_extractors_of_factory(factory: ExtractorFactory) -> List[Extractor]:
    factory_name = type(factory).__name__
    try:
        extractors = list(factory.create_extractors())
    except Exception as e:
        logger.error("Extractor factory %s failed: %s", factory_name, e)
        raise ExtractionError(
            "Extractor factory %s failed: %s" % (factory_name, e)
        ) from e
    logger.info(
        "Factory %s created extractors %s",
        factory_name,
        [extractor.name() for extractor in extractors]
    )
    return extractors
