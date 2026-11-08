---
name: error-to-rule
description: Use after an agent error: a broken build, a secret, a bypassed rule, an invented API, a barrier that fires again and again. Turns the error into a barrier, a repro and a rule line.
---
# Error to rule

The model does not remember between sessions. The environment must remember. Each agent error must become a barrier. Without a barrier, the error comes back.

## Procedure
1. Add an entry to `error.md` in 24 hours: `./harness.sh incident . "what happened"`. Fill in `Found by`.
2. Find the root cause. Write it in one sentence. Write the class of the error, not the case: "regex reads the next line", not "bug in parse.py".
3. Select the deepest barrier level. The order is OS > server > hook > text.
4. Make the barrier for the class. It must also stop variants that you did not see.
5. Write a repro. It must fail before the barrier and pass after it. Add it as an attack to `try-it.sh` when the barrier is in this kit.
6. Teach the agent. The block message says what to do instead. A new session does not remember it. Add one rule line to `AGENTS.md` or a skill.
7. Fill in `Barrier` (the ID, for example B21), `Level`, `Repro`, `Closed`. Set `Status: closed`.
8. Send the change to harness review.
9. After 7 days, open `./harness.sh dashboard`. The incident must show "agent does not try". If it shows "barrier holds, agent tries", fix the instruction from step 6. If it shows "leak", the barrier is too narrow: go to step 4.

## Do not
- Do not write a rule with no check, for example "write clean code".
- Do not make a barrier weaker to make a test pass.
- Do not close an incident with a barrier that stops only the one command you saw.
