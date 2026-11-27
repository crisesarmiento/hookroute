"""Canonical event and stateless routing, independent of the CLI."""

import re
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from pathlib import PurePosixPath
from typing import Protocol
from urllib.parse import urlsplit


class InputError(ValueError):
    """A validation error with a static message safe for CLI output."""


class State(StrEnum):
    WORKING = "working"
    BLOCKED = "blocked"
    WAITING = "waiting"
    DONE = "done"


def _text(value: object) -> bool:
    return (
        isinstance(value, str) and bool(value) and value == value.strip()
        and all(char.isprintable() for char in value)
    )


def _path(value: str, message: str) -> str:
    if not _text(value) or not value.startswith("/") or value.startswith("//"):
        raise InputError(message)
    path = PurePosixPath(value)
    if ".." in path.parts:
        raise InputError(message)
    return str(path)


def _valid_url(value: object) -> bool:
    if not isinstance(value, str) or not re.fullmatch(
        r"[a-zA-Z0-9:/.%@!\[\]$&'()*+,;=_~\-]+", value
    ) or re.search(r"%(?![0-9a-fA-F]{2})", value):
        return False
    try:
        url = urlsplit(value)
        # urlsplit checks malformed bracketed hosts; accessing port checks its range.
        port = url.port
        if url.scheme not in ("http", "https") or not url.hostname or port == 0:
            return False
        if url.netloc.startswith("["):
            return bool(re.fullmatch(r"\[[0-9a-fA-F:.]+\](?::[0-9]+)?", url.netloc))
        label = r"[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?"
        return bool(re.fullmatch(rf"{label}(?:\.{label})*\.?(?::[0-9]+)?", url.netloc))
    except ValueError:
        return False


@dataclass(frozen=True, slots=True, repr=False)
class Event:
    repo: str
    workspace: str
    workspace_path: str
    branch: str
    state: State
    timestamp: datetime
    head_sha: str | None = None
    pr_open: bool | None = None
    git_remote: str | None = None

    def __post_init__(self) -> None:
        if not all(_text(value) for value in (self.repo, self.workspace, self.branch)):
            raise InputError("repo, workspace and branch must be nonempty text")
        object.__setattr__(self, "workspace_path", _path(
            self.workspace_path, "workspace_path must be an absolute POSIX path without '..'"
        ))
        if not isinstance(self.state, State):
            raise InputError("invalid event state")
        if not isinstance(self.timestamp, datetime) or self.timestamp.utcoffset() is None:
            raise InputError("timestamp must have a timezone")
        if self.head_sha is not None and (
            not isinstance(self.head_sha, str)
            or not re.fullmatch(r"(?:[0-9a-fA-F]{40}|[0-9a-fA-F]{64})", self.head_sha)
        ):
            raise InputError("head_sha must be a full Git object ID")
        if self.pr_open is not None and type(self.pr_open) is not bool:
            raise InputError("event pr_open must be a boolean")
        if self.git_remote is not None and not _text(self.git_remote):
            raise InputError("event git_remote must be nonempty text")


@dataclass(frozen=True, slots=True, repr=False)
class Route:
    name: str
    states: frozenset[State]
    url: str
    folder: str | None = None
    git_remote: str | None = None
    repo: str | None = None
    workspace: str | None = None
    pr_open: bool | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not re.fullmatch(
            r"[a-z][a-z0-9_-]{0,31}", self.name
        ):
            raise InputError("invalid route name")
        if not isinstance(self.states, frozenset) or not self.states or not all(
            isinstance(state, State) for state in self.states
        ):
            raise InputError("invalid route states")
        if not _valid_url(self.url):
            raise InputError("route url must be HTTP(S) without credentials, query or fragment")
        if all(value is None for value in (self.folder, self.git_remote, self.repo, self.workspace)):
            raise InputError("route must have at least one selector")
        if self.folder is not None:
            object.__setattr__(self, "folder", _path(
                self.folder, "folder must be an absolute POSIX path without '..'"
            ))
        if any(value is not None and not _text(value)
               for value in (self.git_remote, self.repo, self.workspace)):
            raise InputError("route selectors must be nonempty text")
        if self.pr_open is not None and type(self.pr_open) is not bool:
            raise InputError("route pr_open must be a boolean")


class PROpenResolver(Protocol):
    def __call__(self, event: Event, /) -> bool | None:
        """Return None if the PR status is unknown."""


@dataclass(frozen=True, slots=True)
class Decision:
    rule: str | None
    would_send: bool
    reason: str


def decide(
    event: Event, routes: Iterable[Route], *, pr_open_resolver: PROpenResolver | None = None
) -> Decision:
    """Apply the first complete match; an unknown PR status matches neither boolean."""
    path = PurePosixPath(event.workspace_path)
    pr_open = event.pr_open
    needs_lookup = pr_open is None and pr_open_resolver is not None
    saw_unknown = False
    for route in routes:
        if event.state not in route.states or (
            route.folder is not None and not path.is_relative_to(route.folder)
        ) or any(
            expected is not None and expected != actual
            for expected, actual in (
                (route.git_remote, event.git_remote),
                (route.repo, event.repo),
                (route.workspace, event.workspace),
            )
        ):
            continue
        if route.pr_open is not None:
            if needs_lookup and pr_open_resolver is not None:
                pr_open = pr_open_resolver(event)
                needs_lookup = False
            if type(pr_open) is not bool:
                saw_unknown = True
                continue
            if pr_open != route.pr_open:
                continue
        return Decision(route.name, True, "rule_matched")
    return Decision(None, False, "pr_open_unknown" if saw_unknown else "no_rule_matched")
