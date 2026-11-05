---
name: async-boundary
description: Use when you write or change async handlers, event loops or request pipelines. Stops blocking I/O inside async code.
---
# Async boundary

Blocking I/O inside an async handler stops the event loop. All requests then wait.

## Rules
- Do not call blocking I/O inside `async def`, goroutine pipelines or event handlers.
- Use the async client of the library (`httpx.AsyncClient`, `aiofiles`, `asyncpg`).
- When no async client exists, move the call to a worker pool (`run_in_executor`, a job queue).
- Set a timeout on each external call.

## Check before you finish
1. Search the diff for `requests.`, `time.sleep`, `open(` and `urllib` inside async functions.
2. Run the async-boundary lint rule, if the project has one.
3. Run the tests for the changed handler only.

## Origin
The agent put `requests.get()` inside an async packet handler. Latency went up for all calls.
