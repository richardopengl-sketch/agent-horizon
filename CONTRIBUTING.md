# Contributing

Agent Horizon is intentionally small. Changes should preserve the trajectory-aware security model while keeping the demo deterministic and easy to validate.

## Development loop

1. Create a focused branch.
2. Make the smallest change that satisfies the goal.
3. Run:
   - `python -m pytest -q`
   - `python -m ruff check .`
   - `python -m mypy core scenarios`
   - `python scripts/validate_repo.py`
4. Open a pull request using the repository template.
5. Address CI failures before requesting review.

## Architectural invariants

- `core/` owns state reduction, delta assessment, and policy decisions.
- `scenarios/` provides deterministic inputs and does not own policy.
- `app.py` presents results and must not redefine policy behavior.
- Semantic Delta asks what became newly knowable.
- Consequence Delta asks what became newly possible.
- Low-contribution events must not increase risk merely because event volume increased.
- High-impact boundary transitions must remain explicit and reviewable.

## Pull request expectations

Explain the goal, affected invariant, validation evidence, and rollback/containment plan.
Do not commit secrets, generated videos, local virtual environments, or machine-local artifacts.
