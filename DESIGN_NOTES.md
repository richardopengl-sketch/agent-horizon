# Agent Horizon — Implementation Notes

## Core invariant

**Security and privacy are properties of the trajectory, not just the individual event.**

## Mechanism vs policy

The reducer is the mechanism: it maintains compact state. Delta evaluators and policy rules are replaceable policy modules.

## FP / smokescreen handling in the MVP

Evidence uses trust × relevance as a contribution score. Low-contribution events are ignored by the contextual state and counted separately. The demo also models evidence independence via `independent_group` so event count is not treated as evidence count.

## Fast path / slow path

The fast path is deterministic. `core/slow_path.py` contains a deterministic stand-in for a future semantic evaluator. It exists to demonstrate the architectural seam without introducing a network dependency.

## Production questions intentionally left open

- How to calibrate semantic novelty and sensitivity in a specific enterprise domain.
- How state should expire or cross agent/session boundaries.
- How to sign/attest provenance metadata from third-party runtimes.
- How to set thresholds per action reversibility and blast radius.
- How to evaluate privacy-specific deltas without over-collecting raw data.
