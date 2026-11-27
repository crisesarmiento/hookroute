---
name: sharpen
description: Deepen and rewrite a task without enlarging its scope. Use only on request, before handing off a vague or under-specified task.
metadata:
  source: pstack 0.15.46
  author: Lauren Tan
  license: MIT
  attribution: Adapted from pstack; see NOTICE.md in cstack.
---

# Sharpen

Restate the goal and smallest change in one or two lines. Read the prompt and
relevant repository context; do not implement.

Give four short answers:

1. What would a top professional do here that was not asked for?
2. What is the rawest material they would start from?
3. What specific methods and tools would they use?
4. What, besides the agent or user, would show the result is right?

Rewrite the prompt to ask for exactly that. Add evidence, methods, and an
independent “how we'll know it's right” check, not scope. Preserve constraints;
introduce no model, provider, or harness roles unless the user named them.

Request throwaway prototypes for experimentally decidable choices and an
observed recommendation. Leave product and preference choices to the user.
Do not request implementation needing approval first; end with the decision
to bring back.

Never read, print, or store secrets. Propose only; do not commit, merge, push,
or deploy.
