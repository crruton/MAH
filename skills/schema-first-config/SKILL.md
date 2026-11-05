---
name: schema-first-config
description: Use when you change structured content: configs, scenarios, prompts as data. Changes it only through a schema.
---
# Schema-first config

Free text in a structured file breaks the parser at runtime, not in review.

## Rules
- Find the JSON Schema of the file before you change it.
- Change the file through the `schema-store` MCP server: `propose_patch` and `apply_patch`.
- When no schema exists, write the schema first. Ask the human to approve it.
- Do not edit the file as plain text.

## Check before you finish
1. The file is valid against its schema.
2. The parser test for this file passes.

## Origin
The agent wrote dialog scenarios as free text. The parser failed in production.
