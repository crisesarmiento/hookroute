# hookroute

Commands and paths below are what this repository actually has. When a
command does not exist yet, it is written as such; do not invent a green
result.

## Build and test

- Install: not required yet (no runtime package in the tree).
- Test: not defined yet. The first runtime issue must add a single `verify`
  command from the repository root (core unit tests; later also
  `orca plugin validate .` once `orca-plugin.json` exists).
- Focused verification: the same `verify` command, or the narrowest test
  file the issue names, once it exists.
- Architecture and domain vocabulary: [docs/SPEC.md](docs/SPEC.md).

## Review

Look at evidence before the diff: show the command, exit status and
observable result for the changed behavior. Name checks you could not run
and why. Do not declare work done without that verification.

## Workflow

- One issue = one branch = one small pull request. Stay inside the issue's
  scope; if the work grows, stop and open another issue.
- Never push to the default branch (`main`). Open a PR instead.
- Do not force-push to the default branch, and do not delete it.
- Open pull requests ready for review, never as drafts (for example no
  `gh pr create --draft`); reviews run once, when the PR opens.
- Use conventional commit messages (`feat:`, `fix:`, `docs:`, `test:`,
  `chore:`, `refactor:`, `ci:`).
- Squash merge only, after the maintainer accepts the PR (and CI is green
  once CI exists).
- Do not commit secrets, credentials, `.env` files, tokens, private keys,
  or unredacted logs. Do not put secrets in versioned config (`routes.toml`,
  settings committed to git) or print them in logs.
- Do not install tools, dependencies, or services unless the issue or the
  maintainer asked for them.
- Do not weaken, skip, or delete tests just to go green.
- Never pre-allow push, pull request operations, merge, sudo, or secret
  reads. Variable arguments stay on ask. Confirm prompts interactively.

## Shared guidance

- Implementation checklist: [docs/PRINCIPLES.md](docs/PRINCIPLES.md).
- MVP contract: [docs/SPEC.md](docs/SPEC.md).
- Pinned shared skills (cstack v0.1.1): `.agents/skills/correct` and
  `.agents/skills/sharpen` (see `.opencode/cstack.lock.json`).
- A project-specific `verify-hookroute` skill is not generated yet. Do not
  vendor cstack's `verify-template`.

Checkable rules do not belong here: put them in types, lint, tests or CI.
Keep this file for context; use short skills for judgment.

`AGENTS.md` is canonical. The relative symlink `CLAUDE.md -> AGENTS.md` is
committed at the repository root.
