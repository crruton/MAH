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
- Barrier: the demo reset uses --no-verify. The error statistics show repeats, so a human sees the noise
- Level: text
- Repro: run try-it.sh. B02 must show 1 event
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
- Barrier: write patch scripts to a file. Use the Edit tool for lines with backslashes. Do not use sed for code
- Level: text
- Repro: no machine check. The error statistics show it as a repeat class
- ADR: -
- Status: closed
