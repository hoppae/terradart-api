import logging
from typing import Any, Mapping, cast

API_FAILURE_LOGGER = logging.getLogger("terradart.api_failures")


def _normalize_level(level: int | str) -> int:
    if isinstance(level, int):
        return level
    normalized = getattr(logging, level.upper(), None)
    if isinstance(normalized, int):
        return normalized
    return logging.WARNING


def _format_context(context: Mapping[str, Any] | None) -> str:
    if not context:
        return ""
    parts: list[str] = []
    for key, value in context.items():
        parts.append(f"{key}={value}")
    return " ".join(parts)


def log_api_failure(name: str, triggered: bool = True, context: Mapping[str, Any] | None = None,
    *, reason: str | None = None, level: int | str = logging.WARNING) -> None:

    resolved_level = _normalize_level(level)
    context_string = _format_context(context)
    base_msg = f"external failure '{name}' {'triggered' if triggered else 'checked'}"

    if reason:
        base_msg = f"{base_msg}: {reason}"
    if context_string:
        base_msg = f"{base_msg} | {context_string}"

    API_FAILURE_LOGGER.log(
        resolved_level,
        base_msg,
        extra = {
            "external_failure_name": name,
            "external_failure_triggered": triggered,
            "external_failure_context": cast(Mapping[str, Any], context or {}),
        },
    )

