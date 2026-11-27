# hookroute

A local, stateless webhook router for coding agents (Orca, OpenCode, and later
other harnesses). It matches an agent event by repository, workspace, state,
and optional conditions (for example “the branch has an open pull request”),
then fires a webhook only when the match survives dedupe, cooldown, and a
circuit breaker.

hookroute is a starting point for this project, not an official product of
Orca, OpenCode, or any other organization.

## Why

A machine-wide “notify on every `done` / `waiting` / `blocked`” filter wakes
the wrong receivers and burns tokens. hookroute keeps routing on the local
machine, with no footprint in other people’s repositories, and drops events
before any HTTP call when they do not match a rule.

## Architecture

Three layers share one testable core. There is no hookroute daemon.

1. **Core router** — versionable rules (planned: `routes.toml`), match,
   state stability, start-screen filter, dedupe, cooldown, circuit breaker,
   and `--dry-run`. Secrets are never in the config file.
2. **Orca plugin** — a `trusted-worker` plugin (`orca-plugin.json` manifest
   v2 at the repository root) that listens for `agent.status.changed` and
   calls the core. Secrets live in Orca’s `secrets:own` store; dedupe state
   in `storage:own`.
3. **OpenCode adapter and CLI** — a thin OpenCode plugin and a CLI that
   feed the same core. The CLI supports `--dry-run`. During the MVP the
   OpenCode plugin loads from a local path, not from npm.

See [docs/SPEC.md](docs/SPEC.md) for the MVP contract, verified Orca plugin
requirements, and the planned publishing steps.

## Status

The specification and agent setup live on the default branch once the first
docs pull request merges. Runtime code (core, CLI, plugins) is not in the
tree yet. Implementation is split into small issues, one branch and one pull
request each, in this order:

1. Core router, `routes.toml`, and CLI `--dry-run`, with unit tests.
2. Dedupe, cooldown, circuit breaker, and persistence across restarts.
3. Orca plugin layer, validated with `orca plugin validate`.
4. OpenCode adapter, start-screen filter, and local usage docs.

## Development

Commands will land with the first runtime issue. Until then there is no
install, lint, test, or build step. The planned single `verify` command will
run the core tests and, once the Orca plugin exists, `orca plugin validate .`.

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
