import dataclasses
import datetime
import json
from typing import Any, Callable, Dict

ValueFormatter = Callable[[Any], Any]


def to_json_compatible(value: Any) -> Any:
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return dataclasses.asdict(value)
    elif isinstance(value, (datetime.date, datetime.datetime)):
        return value.isoformat()
    elif isinstance(value, (set, frozenset, tuple)):
        return list(value)
    else:
        raise TypeError(
            "Value of type %s is not JSON serializable" % type(value).__name__
        )


def format_as_json(value: Any) -> str:
    return json.dumps(value, default=to_json_compatible, indent=2)


def format_as_is(value: Any) -> Any:
    return value


VALUE_FORMATTERS: Dict[str, ValueFormatter] = {
    "": format_as_is,
    "json": format_as_json,
}


def ensure_format_is_supported(output_format: str) -> None:
    if output_format not in VALUE_FORMATTERS:
        raise ValueError(
            "Format '%s' not supported. Supported formats: %s"
            % (output_format, ", ".join(f for f in VALUE_FORMATTERS if f))
        )
    else:
        return None


def format_value(value: Any, output_format: str) -> Any:
    ensure_format_is_supported(output_format)
    return VALUE_FORMATTERS[output_format](value)
