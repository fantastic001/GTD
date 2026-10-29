from typing import Any, Callable, Dict, Mapping, Optional, Sequence

from gtd.extraction.errors import ConflictingOutputError

MergeStrategy = Callable[[Sequence[Any]], Any]


def concatenate_lists(values: Sequence[list]) -> list:
    return [item for value in values for item in value]


def union_disjoint_dicts(values: Sequence[dict]) -> dict:
    merged: dict = {}
    for value in values:
        overlapping_keys = merged.keys() & value.keys()
        if overlapping_keys:
            raise ConflictingOutputError(
                "Overlapping entries: %s" % list(overlapping_keys)
            )
        else:
            merged.update(value)
    return merged


DEFAULT_MERGE_STRATEGIES: Dict[type, MergeStrategy] = {
    list: concatenate_lists,
    dict: union_disjoint_dicts,
    int: sum,
    float: sum,
}


class ContextValueMerger:

    def __init__(
        self,
        strategies: Optional[Mapping[type, MergeStrategy]] = None
    ) -> None:
        self._strategies = dict(
            DEFAULT_MERGE_STRATEGIES if strategies is None else strategies
        )

    def merge(self, key: str, values: Sequence[Any]) -> Any:
        if len(values) == 0:
            raise ValueError("No values to merge for key '%s'" % key)
        elif len(values) == 1:
            return values[0]
        else:
            return self._merge_contributions(key, values)

    def _merge_contributions(self, key: str, values: Sequence[Any]) -> Any:
        value_types = {type(value) for value in values}
        if len(value_types) != 1:
            raise ConflictingOutputError(
                "Key '%s' produced with different types: %s"
                % (key, sorted(t.__name__ for t in value_types))
            )
        strategy = self._strategies.get(value_types.pop())
        if strategy is None:
            raise ConflictingOutputError(
                "Key '%s' produced by multiple extractors but values of "
                "type %s cannot be merged" % (key, type(values[0]).__name__)
            )
        else:
            return self._apply_strategy(strategy, key, values)

    def _apply_strategy(
        self,
        strategy: MergeStrategy,
        key: str,
        values: Sequence[Any]
    ) -> Any:
        try:
            return strategy(values)
        except ConflictingOutputError as e:
            raise ConflictingOutputError(
                "Cannot merge key '%s': %s" % (key, e)
            ) from e
