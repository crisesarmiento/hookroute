---
name: correct
description: Find recurring repository mistakes and prevent them structurally. Use when the user asks to fix a mistake that recurs (seen at least twice) or corrects an agent for breaking an existing rule.
metadata:
  source: pstack 0.15.46
  author: Lauren Tan
  license: MIT
  attribution: Adapted from pstack; see NOTICE.md in cstack.
---

# Correct

Assume every contributor is an agent that sees only the files it opened.
Make mistakes impossible rather than asking contributors to remember more.

1. Inspect recent commits, reverts, review comments, `AGENTS.md`, and comments
   explaining workarounds. Include the user's correction, if supplied.
   Group by mistake class, not symptom. Count a class only after two evidenced
   occurrences; honestly report when none qualify. Do not invent evidence.
2. Choose the highest effective level, in order:
   - Architecture: remove the invalid path or centralize the invariant.
   - Types: make invalid states unrepresentable.
   - Lint or CI: reject the pattern with an error naming the fix.
   - Behavior test: exercise the real failure.
   - Instructions last: put unavoidable judgement in a short skill and context
     in `AGENTS.md`; explain why stronger enforcement cannot work.
3. Propose new dependencies or CI jobs instead of adding them. If approval is
   needed, stop with the proposed change. Reuse existing checks where possible,
   running the same command locally and in CI.
4. For each eligible class, implement one focused fix. Prove its check fails
   on a real past mistake and passes on the fixed code. Record the exact command,
   exit status, and relevant output for both. Isolate historical reproduction;
   never discard unrelated work. If reproduction is impossible, report the
   blocker rather than claiming proof.
5. For widespread legacy patterns, fail only on new occurrences. Put exceptions
   on the offending line with a reason, expiry date, and human approval.
6. Update the existing rule table, pairing each rule with its enforcement.
   If none exists, propose a location (e.g. `docs/rules.md` linked from `AGENTS.md`)
   rather than growing that context file. Remove obsolete
   instructional rules once their mistakes cannot happen.
7. Make one local commit per fixed class, including its failing/passing proof
   in the commit message. Stop there: do not open a PR, merge, push, or deploy.

Reply with each class, its evidence links or commit references, chosen level,
why each higher level could not work, enforcement and proof, and local commit
or blocker. Include the updated rule/enforcement table.

Never read, print, or store secret values, environment-file contents, tokens,
or keys; refer to environment variables by name only.
