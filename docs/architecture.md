# Architecture

## Mission

Agent Horizon is a trajectory-aware contextual impact layer for agentic systems.

> Given the trajectory so far, what has become newly knowable or newly possible, and what control should apply before the next boundary is crossed?

## System flow

```text
Agent / MCP / A2A / Tool event
            |
            v
      AgentEvent model
            |
            v
      State Reducer
            |
            v
   ContextualState (compact)
            |
            v
       Delta Engine
      /           \
Semantic Delta   Consequence Delta
      \           /
       v         v
      Impact Assessment
            |
            v
       Policy Engine
            |
            v
Allow / Audit / Constrain / Require Approval / Block
```

## Component boundaries

- `core/models.py`: shared event, evidence, state, assessment, and decision types.
- `core/state_reducer.py`: deterministic state-transition boundary.
- `core/delta_engine.py`: detects semantic/consequence change.
- `core/policy_engine.py`: converts assessed change into a decision.
- `core/slow_path.py`: optional semantic reassessment hook for ambiguous cases.
- `scenarios/`: deterministic demo inputs only.
- `app.py`: presentation layer only.
- `automation/`: recording/narration tooling, outside the runtime security model.

## Key invariants

1. Event count is not risk.
2. Provenance is preserved.
3. Boundary transitions are explicit.
4. Policy is separated from UI.
5. Scenarios do not own policy.
6. Routine events stay on a deterministic fast path.

## Validation loop

```text
change -> pytest -> Ruff -> mypy -> machine-readable validation report -> CI artifact -> human review -> merge
```

`python scripts/validate_repo.py` writes `.reports/validation-report.json`.

## Failure containment

A failing change remains isolated on its branch, CI blocks the PR, validation artifacts identify failed checks, and rollback is a normal Git revert. No workflow auto-merges code or mutates production resources.
