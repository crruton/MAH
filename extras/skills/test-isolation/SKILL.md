---
name: test-isolation
description: Use when you write tests that need a database or another shared resource. Gives each test its own data and a lease.
---
# Test isolation

Tests that write to a shared test database break other agents and other tests.

## Rules
- Do not connect to a shared test database directly.
- Get a test environment from the `test-env-broker` MCP server: `reserve_test_env` and `release_test_env`.
- Give each test its own data scope (a schema, a tenant, a transaction that you roll back).
- Release the lease in a `finally` block or a fixture teardown.

## Check before you finish
1. Search the tests for hardcoded database URLs.
2. Run the changed tests two times in parallel. Both runs must pass.

## Origin
Solo stage: one fixture per test was sufficient. Team stage: 20 agents locked one database. The skill now uses leases.
