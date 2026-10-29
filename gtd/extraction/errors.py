class ExtractionError(Exception):
    pass


class MissingDependencyError(ExtractionError):
    pass


class CyclicDependencyError(ExtractionError):
    pass


class ConflictingOutputError(ExtractionError):
    pass


class ExtractorContractError(ExtractionError):
    pass


class ExtractorFailedError(ExtractionError):
    pass
