# ADR 0001: Separate compact trajectory state from delta and policy evaluation

- Status: Accepted
- Date: 2026-09-14

## Context

Agent Horizon must reason across a sequence of otherwise legitimate actions without making the entire raw event history the policy input.

## Decision

Use a compact `ContextualState` updated by a deterministic reducer, then evaluate meaningful change as a separate Delta step and map it to policy.

```text
Event -> State -> Delta -> Impact -> Policy
```

## Consequences

Benefits: deterministic transitions, testable policy, noise filtering, common lifecycle for semantic and consequence deltas.
Trade-offs: the state schema is a compatibility boundary and reducer changes require regression tests.
