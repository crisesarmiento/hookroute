# Implementation principles

One checklist for planning, implementation and review; use the items that apply.
Adapted from [pstack 0.15.46](https://github.com/cursor/plugins/tree/0b46ec3/pstack)
by Lauren Tan (Copyright © 2026 Lauren Tan), MIT.
The upstream MIT license (Copyright © 2026 Lauren Tan) is reproduced below.

- [ ] **attack-the-premise**
  - Rule: After two fixes fail the same gate, test their shared premise before another fix.
  - Applies: Repeated failed repairs or explanations that survive only by adding exceptions.
  - You broke it if: A third patch repeats the same assumption without stating it
    and checking an observation that would differ if it were false.

- [ ] **subtract-before-you-add**
  - Rule: Remove obsolete work and unnecessary complexity before adding machinery.
  - Applies: Evolving a system, replacing a path, or considering speculative edge cases.
  - You broke it if: A new wrapper, validator or fallback preserves a dead path
    that could have been removed instead.

- [ ] **prove-it-works**
  - Rule: Check the real artifact and observable behavior, not a proxy or self-report.
  - Applies: Every claim that a change works, including delegated work.
  - You broke it if: A passing build or an agent's summary is the only evidence
    for a user-visible behavior; first check that a failing observation is valid.

- [ ] **model-the-domain**
  - Rule: Represent domain states and transitions directly so invalid combinations disappear.
  - Applies: Scattered flags, repeated branches or implicit relationships obscure the domain.
  - You broke it if: Contradictory states remain constructible and every caller
    must remember another guard; keep simple, stable code boring.

- [ ] **sequence-verifiable-units**
  - Rule: Order small units so each ends in a checked state before the next begins.
  - Applies: Migrations, sweeps, multi-step changes and experiments.
  - You broke it if: You start the next batch before checking the last one,
    or show a fix without first establishing the failing case or baseline.

- [ ] **separate-before-serializing-shared-state**
  - Rule: Eliminate shared writes first; serialize structurally only when sharing is essential.
  - Applies: Concurrent agents or processes writing the same file, branch, key or object.
  - You broke it if: Writers share a target by convenience, or rely on
    "take turns" instructions instead of separate targets, a lock or a single writer.

- [ ] **laziness-protocol**
  - Rule: Consolidate each decision in one source of truth and minimize the solving diff.
  - Applies: Refactoring, repeated choices, or temptation to add layers and abstractions.
  - You broke it if: The same choice is recomputed in several places, or
    boilerplate grows when one decision passed as a simple flag would suffice.

- [ ] **explain-the-number**
  - Rule: Define the decision before measuring, then report spread, confounders and the limiter.
  - Applies: Before running, trusting or acting on a benchmark, evaluation or other metric.
  - You broke it if: A claimed improvement lacks run count and spread, the
    predeclared decision threshold/noise floor, or an observed reason it was not double.
    Stop if spread exceeds the effect; rule out errors, skipped/cached work,
    unequal tuning and small samples with evidence from the measured run.


---

MIT License

Copyright (c) 2026 Lauren Tan

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
