# Agent rules (lean)

The short layer: only the rules that prevent the damage classes of error.md. The barriers of guard.sh stop the same actions; these rules give the agent the correct way, so it does not hit a barrier.

## Work of other people
- Before you change the state of git, run `git status`. Keep each uncommitted change that the task does not name.
- To put local work aside, use `git stash push --include-untracked`. Do not use `git reset --hard`, `git clean` or a checkout of a folder.
- When a push is rejected, get the remote work first: `git pull --rebase`, then push. Do not force push.

## Checks
- When a hook or a test fails, fix the cause in the code.
- Do not skip hooks, do not change hooks, do not skip or weaken tests.

## Secrets
- Do not read or print `.env`, credentials or keys. Let the code read them at run time.

## Edits
- In a long file, change only the lines you need with the Edit tool. Do not write the file again. Do not replace code with a comment.
- Open text files with an explicit encoding.
- Run the project command exactly as the task gives it.

## Finish
- Do not ask questions: decide and finish the task. Say what you kept and what you changed.
