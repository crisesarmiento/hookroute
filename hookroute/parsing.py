"""Strict, side-effect-free JSON and TOML parsers."""

import json
import re
import tomllib
from datetime import datetime

from .core import Event, InputError, Route, State


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise InputError("duplicate event field")
        result[key] = value
    return result


def _invalid_constant(_: str) -> None:
    raise InputError("invalid JSON event")


def _state(value: object, message: str) -> State:
    try:
        return State(value)
    except ValueError:
        raise InputError(message) from None


def _timestamp(value: object) -> datetime:
    message = "timestamp must be an ISO date and time with a timezone"
    if not isinstance(value, str) or not re.fullmatch(
        r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}"
        r"(?:\.[0-9]{1,6})?(?:Z|[+-](?:[01][0-9]|2[0-3]):[0-5][0-9])",
        value,
    ):
        raise InputError(message)
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        raise InputError(message) from None


def parse_event(source: str) -> Event:
    try:
        data = json.loads(source, object_pairs_hook=_unique_object, parse_constant=_invalid_constant)
    except InputError:
        raise
    except (ValueError, RecursionError):
        raise InputError("invalid JSON event") from None
    required = {"repo", "workspace", "workspace_path", "branch", "state", "timestamp"}
    optional = {"head_sha", "pr_open", "git_remote"}
    if not isinstance(data, dict) or not required <= data.keys() or data.keys() - required - optional:
        raise InputError("invalid event fields")
    data["state"] = _state(data["state"], "invalid event state")
    data["timestamp"] = _timestamp(data["timestamp"])
    return Event(**data)


def parse_routes(source: str) -> tuple[Route, ...]:
    try:
        data = tomllib.loads(source)
    except (ValueError, RecursionError):
        raise InputError("invalid routes TOML") from None
    if data.keys() != {"routes"} or not isinstance(data["routes"], list):
        raise InputError("routes config must contain a routes array")
    routes: list[Route] = []
    names: set[str] = set()
    required = {"name", "states", "url"}
    optional = {"folder", "git_remote", "repo", "workspace", "pr_open"}
    for entry in data["routes"]:
        if not isinstance(entry, dict) or not required <= entry.keys() or entry.keys() - required - optional:
            raise InputError("invalid route fields")
        if not isinstance(entry["states"], list) or not entry["states"]:
            raise InputError("invalid route states")
        states = frozenset(_state(value, "invalid route states") for value in entry["states"])
        if len(states) != len(entry["states"]):
            raise InputError("duplicate route state")
        route = Route(**(entry | {"states": states}))
        if route.name in names:
            raise InputError("duplicate route name")
        names.add(route.name)
        routes.append(route)
    return tuple(routes)
