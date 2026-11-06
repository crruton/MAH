# Agent error log of self-harness

The agent that wrote this kit made these errors. Each one became a barrier or a fix. Run `./harness.sh errors .` for the statistics.

## INC-2026-11-05-01: re.M pattern read the next line in error.md
- Date: 2026-11-05
- Agent: claude-code
- Where: gates/check-error-log.py
- Symptom: a closed incident with an empty Barrier field passed the gate
- Cause: in `^-\s*Barrier:\s*(.*)$` with re.M, `\s*` matched the newline and read the next field
- Class: portability
- Barrier: B21 check-portability flags re.M patterns with \s
- Level: hook
- Repro: try-it.sh --only B21
- ADR: -
- Status: closed

## INC-2026-11-05-02: the same re.M error in the ADR field parser
- Date: 2026-11-05
- Agent: claude-code
- Where: gates/checks.py
- Symptom: an ADR without Applies To passed check-adr-fields
- Cause: the same `\s*` across lines. The first fix did not become a barrier, so the error came back
- Class: portability, repeat
- Barrier: B21
- Level: hook
- Repro: try-it.sh --only B14 and --only B21
- ADR: -
- Status: closed

## INC-2026-11-05-03: subprocess "bash" started WSL on Windows
- Date: 2026-11-05
- Agent: claude-code
- Where: mcp/servers/redteam_runner.py
- Symptom: redteam-runner found 0 scenarios on Windows
- Cause: CreateProcess looks in System32 first and finds the WSL bash, not Git Bash
- Class: portability
- Barrier: B22 check-portability flags a bare "bash" or "sh" in subprocess
- Level: hook
- Repro: try-it.sh --only B22
- ADR: -
- Status: closed

## INC-2026-11-05-04: the MCP selftest closed stdin before the server answered
- Date: 2026-11-05
- Agent: claude-code
- Where: mcp/selftest.py
- Symptom: 3 of 10 servers gave no tools on mcp 1.30 in CI
- Cause: communicate() sent all JSON-RPC messages and closed stdin. The server stopped before tools/list
- Class: portability, race
- Barrier: B23 check-portability flags communicate() with JSON-RPC input
- Level: hook
- Repro: try-it.sh --only B23
- ADR: -
- Status: closed

## INC-2026-11-05-05: mcp 2.x removed the import that the server used
- Date: 2026-11-05
- Agent: claude-code
- Where: mcp/test_env_broker.py
- Symptom: ModuleNotFoundError: mcp.server.fastmcp
- Cause: requirements said mcp>=1.2 with no upper bound. Version 2 renamed FastMCP to MCPServer
- Class: dependency
- Barrier: B24 check-portability needs an upper bound. CI tests mcp<2 and mcp>=2
- Level: hook
- Repro: try-it.sh --only B24
- ADR: -
- Status: closed

## INC-2026-11-05-06: Cyrillic in a heredoc reached Python as mojibake
- Date: 2026-11-05
- Agent: claude-code
- Where: patch scripts for harness.sh
- Symptom: SyntaxError and broken Russian strings in the patch
- Cause: the Windows console code page (cp1251) decoded stdin of python
- Class: portability, encoding
- Barrier: B25 check-portability needs encoding= for text I/O. Scripts with Cyrillic go to a file
- Level: hook
- Repro: try-it.sh --only B25
- ADR: -
- Status: closed

## INC-2026-11-05-07: scripts lost the exec bit on Windows
- Date: 2026-11-05
- Agent: claude-code
- Where: harness.sh, hooks
- Symptom: CI failed with "Permission denied"
- Cause: git on Windows does not keep the exec bit. Files went to git as 100644
- Class: portability
- Barrier: B26 and B27 check-portability: LF for *.sh and mode 100755
- Level: hook
- Repro: try-it.sh --only B26 and --only B27
- ADR: -
- Status: closed

## INC-2026-11-05-08: the demo counted its own reset as 26 force pushes
- Date: 2026-11-05
- Agent: claude-code
- Where: try-it.sh
- Symptom: B02 showed 26 events after one demo run
- Cause: the reset of the demo repository used git push --force through the pre-push hook
- Class: noise in statistics
- Barrier: the demo runs with a throwaway CLAUDE_CONFIG_DIR and HARNESS_HOME; CI checks that the real error store has no events after the demo
- Level: server
- Repro: CI job demo: the step 'the demo does not write to the real error store'
- ADR: -
- Status: closed

## INC-2026-11-06-01: hooks added 2.5 seconds to each tool call
- Date: 2026-11-06
- Agent: claude-code
- Where: hooks/guard-*.sh
- Symptom: ./harness.sh budget showed about 2000 ms on each Bash call on Windows
- Cause: three hooks, a grep process for each pattern and four jq calls on each tool call
- Class: performance
- Barrier: one guard.sh with one jq call and bash regex. collect-tool-errors.sh skips jq on success. Now about 130 ms
- Level: hook
- Repro: ./harness.sh budget <repo> after install
- ADR: -
- Status: closed

## INC-2026-11-06-02: write_text wrote CRLF on Windows
- Date: 2026-11-06
- Agent: claude-code
- Where: metrics/errors.py, mcp/servers/safe_edit.py
- Symptom: docs/errors.md came out with CRLF. safe-edit would change the line endings of each file that it edits
- Cause: Path.write_text and open("w") translate "\n" to "\r\n" on Windows when newline= is not set
- Class: portability, encoding
- Barrier: B25 also flags write_text and open("w") without newline=
- Level: hook
- Repro: try-it.sh --only B25, and HARNESS_ALL=1 python gates/check-portability.py
- ADR: -
- Status: closed

## INC-2026-11-06-03: backslashes in heredoc and sed broke patch scripts four times
- Date: 2026-11-06
- Agent: claude-code
- Where: patch scripts for install.sh, try-it.sh, metrics/errors.py
- Symptom: sed changed nothing, or "\n" became a real line break and broke the Python syntax
- Cause: the agent put escaped text through two shells (bash heredoc, then sed or python)
- Class: tooling, repeat
- Barrier: B38 guard-syntax for heredocs (from INC-2026-11-06-08) and for sed -i with escapes in code files (from INC-2026-11-06-13)
- Level: hook
- Repro: tests/test_loop.py test_shell_patching_of_code_is_denied
- ADR: -
- Status: closed

## INC-2026-11-06-04: the pack was tied to projects and cost more than it gave
- Date: 2026-11-06
- Agent: claude-code
- Where: install.sh, hooks/guard.sh
- Symptom: the user pointed out four harms: 10 MCP servers in each session, SIP skills as noise, guard-destructive blocked docker compose down -v and rm -rf build, check-changelog on each small change
- Cause: the agent added modules because they existed, not because statistics showed a need. The demo checked only attacks, not normal work
- Class: false positive, cost
- Barrier: global install with a minimal core (MCP and domain skills moved to extras), guard.sh with deny/ask/allow levels, 8 normal actions in the demo that must pass
- Level: hook
- Repro: try-it.sh shows "false positives: 0"; ./harness.sh budget shows about 160 tokens and 110 ms
- ADR: -
- Status: closed

## INC-2026-11-06-05: Git Bash rewrote a "/path" argument for Windows Python
- Date: 2026-11-06
- Agent: claude-code
- Where: install.sh (uninstall of the CLAUDE.md import)
- Symptom: uninstall left the import line in CLAUDE.md
- Cause: MSYS path conversion changed the argument "/harness/AGENTS.md" to "C:/Program Files/Git/harness/AGENTS.md"
- Class: portability
- Barrier: no leading slash in arguments to Windows programs. The global-install CI job checks that uninstall removes the line
- Level: hook
- Repro: CI job global-install
- ADR: -
- Status: closed

## INC-2026-11-06-06: the demo counted "file not found" as a working barrier
- Date: 2026-11-06
- Agent: claude-code
- Where: try-it.sh
- Symptom: with a broken install, 24 of 27 attacks showed "blocked"
- Cause: the demo took any non-zero exit code as a block
- Class: false confidence
- Barrier: an attack counts only when the output has "Blocked by" or "FAIL", or the hook asked. Other failures show "DEMO ERROR"
- Level: hook
- Repro: break gates/ in the demo repository. The demo must show DEMO ERROR, not blocked
- ADR: -
- Status: closed

## INC-2026-11-06-07: three different node errors had one signature
- Date: 2026-11-06
- Agent: claude-code
- Found by: dashboard
- Where: metrics/dashboard.py, signature()
- Symptom: 4 failed calls in 2 sessions in 14 days (raft, technology-radar) under "node:internal<path>:#"
- Signature: Bash: node:internal<path>:#
- Cause: the signature took the first line. For node it is the stack header, so an invalid header, an ESM require and a package export error looked like one error. One of them hid a token leak (INC-2026-11-06-11)
- Class: noise in statistics
- Barrier: signature() skips stack headers and success lines and takes the first line that names an error
- Level: hook
- Repro: tests/test_loop.py test_signature_skips_node_stack_header
- ADR: -
- Status: closed
- Closed: 2026-11-06

## INC-2026-11-06-08: a long heredoc broke the shell quotes, again
- Date: 2026-11-06
- Agent: claude-code
- Found by: dashboard
- Where: patch scripts in technology-radar and arcspace sessions
- Symptom: 3 failed calls in 2 sessions in 14 days: "unexpected EOF while looking for matching `''"
- Signature: Bash: <path>: -c: line #: unexpected EOF while looking for matching `''
- Cause: a quote inside a heredoc script ended the shell string early. INC-2026-11-06-03 had the same class, but it was closed with a text rule only
- Class: tooling, repeat
- Barrier: B38 guard-syntax: bash -n checks each heredoc or long multi-line command before it runs
- Level: hook
- Repro: tests/test_loop.py test_shell_patching_of_code_is_denied; demo attack B38
- ADR: -
- Status: closed
- Closed: 2026-11-06

## INC-2026-11-06-09: the agent read files that do not exist
- Date: 2026-11-06
- Agent: claude-code
- Found by: dashboard
- Where: screenshots that a script did not make, a memory file before it was created
- Symptom: 3 failed calls in 2 sessions in 14 days: "File does not exist"
- Signature: Read: File does not exist. Note: your current working directory is <path>
- Cause: a check of a file that can be absent. The agent gets the answer from one call and continues. This is not an agent error, and a barrier would cost more than the call
- Class: expected failure
- Barrier: -
- Level: -
- Repro: -
- ADR: -
- Status: accepted
- Closed: 2026-11-06

## INC-2026-11-06-10: the signature took a success line
- Date: 2026-11-06
- Agent: claude-code
- Found by: dashboard
- Where: metrics/dashboard.py, signature()
- Symptom: 3 failed calls under "✓ check-syntax: # файлов"
- Signature: PowerShell: ✓ check-syntax: # файлов, # inline-скриптов в # страницах
- Cause: the script printed a success line first and the error later. The same cause as INC-2026-11-06-07
- Class: noise in statistics
- Barrier: the signature() fix of INC-2026-11-06-07
- Level: hook
- Repro: tests/test_loop.py test_signature_skips_success_line
- ADR: -
- Status: closed
- Closed: 2026-11-06

## INC-2026-11-06-11: a GitLab token reached the session transcript through an error message
- Date: 2026-11-06
- Agent: claude-code
- Found by: dashboard
- Where: technology-radar, gl-create-mr.cjs, session of 2026-10-24
- Symptom: node printed "Headers.append: <file content> is an invalid header value". The file content had the token
- Cause: the script sent the whole token file (KEY=value lines) as an HTTP header. The error message of the runtime printed it. The collector mask and the gate check-secrets knew only the old 20-character GitLab format
- Class: secret leak
- Barrier: collector mask and B07 know the new GitLab formats (glpat, gldt, glrt, glptt, glcbt, glsoat with dots); a human rotates the token
- Level: hook
- Repro: tests/test_loop.py test_new_gitlab_token_is_masked, test_new_gitlab_token_fails_the_gate
- ADR: -
- Status: open
- Closed:

## INC-2026-11-06-12: B22 stopped the case, not the class
- Date: 2026-11-06
- Agent: claude-code
- Found by: review
- Where: tests/test_loop.py while closing INC-2026-11-06-08
- Symptom: the agent wrote bash = "bash"; subprocess.run([bash, ...]) and Windows started WSL. The gate B22 did not see it
- Cause: B22 checked only a string literal in the argument list, not a name bound to the same string
- Class: portability, leak
- Barrier: B22 resolves names bound to string constants in the module
- Level: hook
- Repro: tests/test_loop.py test_bare_bash_through_a_variable_fails_the_gate
- ADR: -
- Status: closed
- Closed: 2026-11-06

## INC-2026-11-06-13: sed changed "\n" into a real line break in Python code, again
- Date: 2026-11-06
- Agent: claude-code
- Found by: review
- Where: tests/test_loop.py while closing INC-2026-11-06-08
- Symptom: newline="\n" became newline=" and a line break; no gate saw it, the agent saw it when it read the lines back
- Cause: the same class as INC-2026-11-06-03: escapes through two shells. B38 covered only heredocs
- Class: tooling, repeat
- Barrier: B38 also denies sed -i with \n, \t or \\ in a code file
- Level: hook
- Repro: tests/test_loop.py test_shell_patching_of_code_is_denied
- ADR: -
- Status: closed
- Closed: 2026-11-06
