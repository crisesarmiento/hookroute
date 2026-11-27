# hookroute

A local, stateless webhook router for coding agents (Orca, OpenCode, and later
other harnesses). It matches an agent event by repository, workspace, state,
and optional conditions (for example “the branch has an open pull request”),
then reports whether a rule would send. The current core and CLI never make
HTTP requests. Delivery, dedupe, cooldown, and a circuit breaker are planned
for later issues.

hookroute is a starting point for this project, not an official product of
Orca, OpenCode, or any other organization.

## Why

A machine-wide “notify on every `done` / `waiting` / `blocked`” filter wakes
the wrong receivers and burns tokens. hookroute keeps routing on the local
machine, with no footprint in other people’s repositories, and drops events
before any HTTP call when they do not match a rule.

## Architecture

Three layers share one testable core. There is no hookroute daemon.

1. **Core router and CLI** — versionable `routes.toml` rules, event matching,
   optional `pr_open` checks, and `--dry-run`. Secrets are never in the config
   file. State stability, start-screen filtering, dedupe, cooldown, and circuit
   breaking are not implemented yet.
2. **Orca plugin (planned)** — a `trusted-worker` plugin (`orca-plugin.json` manifest
   v2 at the repository root) that listens for `agent.status.changed` and
   calls the core. Secrets live in Orca’s `secrets:own` store; dedupe state
   in `storage:own`.
3. **OpenCode adapter (planned)** — a thin OpenCode plugin that feeds the
   same core. During the MVP the OpenCode plugin will load from a local
   path, not from npm.

See [docs/SPEC.md](docs/SPEC.md) for the MVP contract, verified Orca plugin
requirements, and the planned publishing steps.

## Status

The core router and stateless CLI are implemented. Adapters and delivery are
not. Implementation is split into small issues, one branch and one pull
request each, in this order:

1. Core router, `routes.toml`, and CLI `--dry-run`, with unit tests.
2. Dedupe, cooldown, circuit breaker, and persistence across restarts.
3. Orca plugin layer, validated with `orca plugin validate`.
4. OpenCode adapter, start-screen filter, and local usage docs.

## Try the CLI

From the repository root:

```sh
./bin/hookroute event --dry-run --file examples/event.json
# Equivalent stdin input:
cat examples/event.json | python3 -m hookroute event --dry-run
```

The CLI reads `routes.toml` by default; use `--routes PATH` for another file.
It prints JSON containing `rule`, `would_send`, `reason`, and `sent: false`.
`would_send` describes routing eligibility, not a delivery attempt. Even
without `--dry-run`, this version only prints a decision and never sends.
Invalid input exits nonzero with a generic error, without echoing input.

### Rules and events

The sample [`routes.toml`](routes.toml) and
[`examples/event.json`](examples/event.json) are safe local examples.
Each `[[routes]]` entry has a unique `name`, a `states` array, a `url`, and
at least one selector: `folder`, `git_remote`, `repo`, or `workspace`.
Selectors in the same rule are combined with **AND**; rules are evaluated
in file order and the first complete match wins.
Rule names are public identifiers matching `[a-z][a-z0-9_-]{0,31}` and
appear in the decision output. Unknown fields and duplicate rule names
are rejected.

- `repo`, `workspace`, and `git_remote` use exact, case-sensitive matching.
  Git remotes are not normalized between SSH and HTTPS forms.
- `folder` matches an absolute POSIX workspace path at that folder or below
  it, by path segment (not a string prefix). It does not inspect the
  filesystem or resolve symlinks.
- `states` accepts `working`, `blocked`, `waiting`, and `done`.
- Optional `pr_open = true` or `false` requires a known matching boolean.
  Unknown does not match either value. The core accepts an injected resolver
  for local checks; the CLI only uses the event's optional `pr_open` and
  does not invoke `git` or `gh`.

Events require `repo`, `workspace` (name), `workspace_path` (absolute POSIX
path), `branch`, `state`, and a timezone-aware ISO/RFC3339 `timestamp`.
`head_sha`, `git_remote`, and boolean `pr_open` are optional.
Optional fields may also be `null`; `head_sha`, when provided, must be a
full 40- or 64-character hexadecimal Git object ID. The router does not
discover missing metadata itself.

Keep destination URLs secret-free: no credentials, query strings, fragments,
or secret-bearing paths. The parser rejects credentials, query strings, and
fragments; it cannot determine whether an arbitrary path contains a secret.
Do not put tokens or headers in this format. Destination URLs and event
metadata are never included in CLI decisions.

## Development

Python 3.11+ is required. No dependencies or installation are needed.

Run the single verification command from the repository root:

```sh
./verify
```

This runs the core and CLI unit tests. There is no separate build or
typecheck step, and no plugin manifest to validate yet.

Agent and review rules: [AGENTS.md](AGENTS.md). Implementation checklist:
[docs/PRINCIPLES.md](docs/PRINCIPLES.md). Shared skills are pinned with
[cstack](https://github.com/crisesarmiento/cstack) v0.1.1
(`.opencode/cstack.lock.json`).

## Publishing (later)

Not part of the functional MVP. After the plugin works and the maintainer
agrees:

- **Orca** has an official community directory:
  [orca.dev/plugins](https://orca.dev/plugins). Listing steps:
  [Add your plugin](https://orca.dev/plugins/add) (validate, push a `vX.Y.Z`
  tag, add the `orca-plugin` topic).
- **OpenCode** has no official plugin marketplace. A later release may
  publish an npm package, installed with `opencode plugin add` or a
  `plugins` entry in `opencode.json`. Docs:
  [Building plugins](https://opencode.ai/docs/build/plugins),
  [Configure plugins](https://opencode.ai/docs/plugins/).

## License

MIT. See [LICENSE](LICENSE). Contributions follow
[CONTRIBUTING.md](CONTRIBUTING.md). Security reports go through
[SECURITY.md](SECURITY.md).
