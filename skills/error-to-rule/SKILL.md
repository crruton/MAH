---
name: error-to-rule
description: Use after an agent error: a broken build, a secret, a bypassed rule, an invented API. Turns the error into a barrier and a test.
---
# Error to rule

Each agent error must become a barrier. Without a barrier, the error comes back.

## Procedure
1. Add an entry to `error.md` in 24 hours: `./harness.sh incident . "what happened"`.
2. Find the root cause. Write it in one sentence.
3. Select the deepest barrier level. The order is OS > server > hook > text.
4. Make the barrier.
5. Write a repro test. It must fail before the barrier and pass after it.
6. Fill in `Barrier`, `Level` and `Repro`. Set `Status: closed`.
7. Send the change to harness review.

## Do not
- Do not write a rule with no check, for example "write clean code".
- Do not make a barrier weaker to make a test pass.
