# Global agent rules

This file is the company layer: culture, security, git and ADR rules. Keep the source in one git repository. Change it only through a merge request. Copy it to `~/.claude/CLAUDE.md` and `~/.config/opencode/AGENTS.md`. The project file `AGENTS.md` wins over this file. Tell the human about each conflict.

## Task loop
1. Read the project `AGENTS.md`, `docs/adr/index.md`, the spec and the code that you change.
2. When the scope or the acceptance criteria are not clear, ask 2 or 3 questions.
3. For a change in more than one file, write a short plan. Give the ADR IDs or write "no applicable ADRs".
4. Do the work in small steps.
5. Run the tests for the changed files, the linter and the build.
6. When you cannot run a check, tell the human.
7. Commit only when the task or the human tells you to commit. Make one commit for one change. Write the subject in the imperative form.
8. When you commit code, add an entry to `CHANGELOG.md`. Update the document of each changed contract.

## Commands
- End each discovery Bash command with `; true`. A missing file or directory must not fail the call.
- Run `git status --short`, `git diff` and the failing command together in one Bash call.
- Run the project command exactly as the task or the README gives it.
- Do not add `python -I` when you run the code of the project. It removes the script directory from the import path.
- Run the test module of the changed file, for example `python -m unittest test_cart`. A hook blocks the full suite.

## Verify
- Before you change behavior that must stay the same, save the output of the unchanged code.
- When the tree is dirty, get the unchanged code with `git show HEAD:<file>` into a separate temporary directory.
- Do not accept "identical" output from two runs that both failed. Check the exit codes first.
- For a rename, replace with word boundaries. Then search for the old name with `grep -rnw <old> . --exclude-dir=.git`. Zero matches must remain.

## Dirty tree
- To undo one bad line, edit that line. Do not restore the file with `git checkout` or `git restore`.
- Keep each uncommitted change that the task does not name. It can be the only copy of human work.
- Name each kept uncommitted change in your report.

## ADR
- Before you plan, compare your paths with `Applies To` of the accepted ADRs.
- Read each accepted ADR that applies.
- When your change conflicts with an accepted ADR, stop. A human must approve a new ADR first.
- When a `Reconsider When` trigger occurred, propose a new ADR with `Supersedes`.
- Do not change old ADRs. Mark them `SUPERSEDED by ADR-NNNN`.
- Get the number of a new ADR from `./harness.sh adr`, not from memory.

## Git
- Work in `dev`. The `main` branch is production. Change `main` only through a merge request.
- Do not commit secrets or `.env` files.
- Do not change generated files or vendored files.
- Do not run `git reset --hard`, `git clean -f`, `git checkout -- .` or a force push. Ask the human.

## Security
- Keep secrets in environment variables or in a secret store.
- Put placeholders in `.env.example`.
- Do not read or change `.env`, keys, certificates or files in `secrets/`.
- When the code needs a value from `.env`, let the code read the file at run time.
- Do not print secret values in command output or in your report.
- Do not write personal data to logs or prompts.

## Errors
- After an agent error, add an entry to `error.md` in 24 hours.
- Make a barrier at the deepest level. The order is OS > server > hook > text.
- Write a repro test for the barrier.
- When the human corrects the same thing two times in a week, add a rule to the context file.

## Do not
- Do not guess the architecture, the commands or the library flags.
- Do not say that you finished the work when a check failed or did not run.
- Do not make checks weaker to get a green build. Do not skip tests. Do not increase timeouts.
