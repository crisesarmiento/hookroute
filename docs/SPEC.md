# hookroute MVP specification

Local, testable webhook routing for coding-agent events. No hookroute daemon.
Secrets never live in versioned config or in logs.

This document is the contract for the first four implementation issues. Each
issue is one branch and one small, ready-for-review pull request.

## Goal

Given an agent event, decide locally whether a webhook should fire:

- match by repository or workspace, by agent state, and by an optional
  condition (for example “the branch has an open pull request”);
- drop the event when it is a state flap, a start screen, a duplicate, or a
  route that is cooling down or has an open circuit;
- only then POST, resolving the secret from a store that is not the config
  file.

The public project is not coupled to any proprietary plugin, bot, or hosted
service.

## Architecture

Three layers. The core does not import Orca or OpenCode APIs. Each adapter
translates a native event into a canonical event and calls the core. The core
decides; the adapter performs the HTTP call.

```
native event (Orca / OpenCode / CLI)
        │
        ▼
  thin adapter  ──►  core router  ──►  match + dedupe + cooldown + breaker?
        │                    │
        │                    ├─ no  → silence (no HTTP)
        │                    └─ yes → adapter POSTs
        ▼
  secrets from the host secret store, the environment, or a 0600 file
```

Canonical event (design, not an Orca type): `repo`, `workspace` / path,
`branch`, `head_sha` when it can be read, `state`, optional conditions such
as `pr_open`, and a timestamp.

### Core router

Versionable rules, planned as `routes.toml` (Orca settings may mirror the
same fields):

- match on folder, git remote, or repository / workspace name;
- filter on state (`working`, `blocked`, `waiting`, `done` — Orca’s official
  vocabulary);
- optional condition, for example `pr_open`, implemented as a local `git` /
  `gh` check, not as an Orca API;
- destination: webhook URL **without** the secret. A `SecretResolver`
  supplies the secret at send time.

Guarantees from day one:

1. **State stability / debounce.** Do not fire on a flap (for example the
   same terminal moving `done` → `waiting` on the same screen). Persist the
   last send: an Orca worker may stop after it has been idle and start again
   (official docs: it “may also stop when it has been idle for a while”;
   the exact timeout is not documented).
2. **Start-screen filter.** Do not alert a `done` that is only the agent’s
   start screen, with no reply and no question. This is product behavior,
   not an Orca API. The adapter supplies optional terminal-tail text.
3. **Dedupe** on `(repo, branch, head_sha, state)` and, when present, a
   terminal or session id. If `head_sha` cannot be read, degrade explicitly
   (for example `(repo, branch, state)` plus cooldown) and document it.
4. **Cooldown** per route, plus a cap on sends per branch per hour.
5. **Circuit breaker** per route: after N consecutive HTTP failures, open
   the circuit for a period, log (without secrets), and do not retry in a
   burst. This is hookroute design, not an Orca API.
6. **CLI `--dry-run`.** Print which rule matched and why a send would or
   would not happen, with no POST.

The core is a library plus a stateless CLI (`hookroute event --dry-run`,
JSON on stdin). Hookroute itself does not run a background process.

### Orca plugin

A `trusted-worker` plugin with `orca-plugin.json` (manifest format 2) at the
**repository root**, as required by Orca’s community directory. Planned
install identity: `crisesarmiento.hookroute` (`id`: `hookroute`). Leave
`publisher` out when `engines.orca` is `>=1.4.246`.

The worker’s **default export** is `activate(orca)` (a named
`export function activate` is not called). It:

- subscribes to `agent.status.changed`;
- resolves workspace, repo, and branch with `workspace.list` /
  `workspace.readContext` and, when needed, the worktree’s git metadata;
- may read the terminal tail with `terminal.read` (host API 1.3) for the
  start-screen filter — set `engines.orca` to `>=1.4.247`, or feature-detect
  with `orca.host.has('terminal.read')`;
- calls the core and, on a match, POSTs using a secret from `secrets:own`;
- persists dedupe and cooldown in `storage:own`.

Declare settings for routes, enabled states, cooldown, and flags. Never
store a token or `Authorization` value in a setting: if one is pasted, move
it to `secrets:own` and clear the setting. If `secrets.protection` returns
`unavailable` (no OS keyring, or Linux `basic_text`), `secrets.set` fails —
surface that in logs or settings and do not write the secret into the repo.

A routes panel is out of scope for the MVP; Settings is enough.

Official references:

- [Writing an Orca plugin](https://github.com/stablyai/orca/blob/main/docs/reference/plugin-authoring.md)
- [Manifest v2](https://github.com/stablyai/orca/blob/main/docs/reference/plugin-manifest.md)
- [Host API 1](https://github.com/stablyai/orca/blob/main/docs/reference/plugin-host-api.md)
- Official example: `examples/plugins/hello-worker-panel` in
  [stablyai/orca](https://github.com/stablyai/orca)
- Schema: `https://raw.githubusercontent.com/stablyai/orca/main/docs/schemas/plugins/orca-plugin.v2.schema.json`

Verified minimum for the MVP:

| Item | Requirement |
| --- | --- |
| Manifest | `manifestVersion: 2`, `execution: "trusted-worker"`, `id`, `name`, `version`, `engines.orca`, `pluginApi: 1`, `main`, `contributes`, `capabilities` |
| `main` | `.js` / `.mjs`, or `.ts` / `.mts` (TypeScript needs `engines.orca` `>=1.4.246`) |
| `contributes.events` | `[{ "on": "agent.status.changed" }]` |
| `contributes.settings` | Routes, states, cooldown, flags (no secrets) |
| Capabilities | `agent:read`, `workspace:read`, `terminal:read`, `settings:own`, `secrets:own`, `storage:own` — and no more for the MVP |
| Worker API | Default export `activate(orca)`; optional `deactivate()` to flush state |
| Event payload | `state` is `working` \| `blocked` \| `waiting` \| `done`; `terminalId` is optional; `paneKey` is **not** (yet) a terminal id accepted by `terminal.sendText` or `terminal.read` |

Do not request `terminal:send`, `agent:launch`, or `workspace:write` in the
MVP. Do not use `contributes.hooks` for routing; hooks intercept actions,
events report status. `contributes.skills` is reserved by Orca and must stay
empty.

Scaffold and validate with the official CLI: `orca plugin create`,
`orca plugin validate .`, `orca plugin inspect`, `orca plugin dev load`.
There is no separate “create an Orca plugin” skill in cstack; use those
commands and the docs above.

**Official gaps** (do not invent; record evidence in the issue):

- Exact worker idle timeout is undocumented; persist state in `storage:own`
  anyway.
- If `terminalId` is missing from an event, do not guess; skip the
  start-screen filter and say so in the log.
- `pr_open` is a local check, not an Orca API.

### OpenCode adapter and CLI

Same core. Official load paths:

- local development: `~/.config/opencode/plugins/`, a path in
  `opencode.json(c)`, or auto-discovery under `.opencode/plugins/`;
- later publication: an npm package (see [Publishing](#publishing-later)).

The adapter is an OpenCode v2 plugin (`Plugin.define` from
[`@opencode/plugin`](https://www.npmjs.com/package/@opencode/plugin)). It
translates native events into the canonical event. The official event
documented for “the session went idle” is `session.idle`, via
`ctx.event.subscribe`. OpenCode docs do **not** define a one-to-one mapping
onto Orca’s `working` / `blocked` / `waiting` / `done`. That mapping is
adapter work and must be verified with evidence in the OpenCode issue.

Docs: [Building plugins](https://opencode.ai/docs/build/plugins),
[Configure plugins](https://opencode.ai/docs/plugins/).

The CLI is the `--dry-run` entry point and, later, a way to attach a third
harness without changing the core.

## Publishing (later)

Not part of the functional MVP. Requires an explicit maintainer ok.

**Orca** has an official community directory:
[orca.dev/plugins](https://orca.dev/plugins). Steps:
[Add your plugin](https://orca.dev/plugins/add) and the
[listing policy](https://github.com/stablyai/orca/blob/main/docs/reference/plugin-listing-policy.md).

1. Public GitHub repository with `orca-plugin.json` (manifest v2) at the
   root, plus a license.
2. `orca plugin validate .` is green.
3. Annotated tag `vX.Y.Z` on the commit whose manifest `version` matches,
   then push the tag.
4. GitHub topic `orca-plugin`.
5. Status page: `https://orca.dev/plugins/crisesarmiento/hookroute`.

The automatic directory flow requires the manifest at the repository root.
A separate Orca *catalog* (`orca-catalog.json`) can pin a subdirectory via
`source.path`; hookroute does not need a catalog for the community listing.

**OpenCode** has no official plugin marketplace or submission form in the
public docs. The documented path is `npm publish` of a package that exports
the plugin, then `opencode plugin add <package>@<version>` or a `plugins`
entry in `opencode.json(c)`. Git specs (`github:crisesarmiento/hookroute`)
also work. The MVP uses a local load only.

## Implementation slices

1. **Core + CLI `--dry-run`.** Parse `routes.toml`, match, print the
   decision, no HTTP. Unit tests. Introduce the first `verify` command
   (test runner).
2. **Dedupe, cooldown, circuit breaker, persistence.** File mode `0600`
   for the CLI; a store interface the Orca plugin later backs with
   `storage:own`. Tests for the tuple, cooldown, breaker, and secret-free
   logs.
3. **Orca plugin.** Manifest, `activate`, events, settings, secrets,
   `orca plugin validate .` green, worker tests against a mocked host.
4. **OpenCode adapter + start-screen filter + local usage docs.** Start
   from `session.idle`. Document, with evidence, which states could be
   mapped. The start-screen filter sits behind a “tail text” interface used
   by Orca (`terminal.read`) and, if OpenCode exposes an equivalent, by
   that adapter; otherwise it is a no-op and the pull request says so.

An Orca routes panel, npm publish, and the `orca-plugin` topic are out of
scope until a later decision.
