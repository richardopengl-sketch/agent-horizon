## Goal
What problem does this PR solve?

## Change
What changed, and which component boundary does it affect?

## Agent / human provenance
- [ ] Human-authored
- [ ] AI-assisted
- [ ] Agent-proposed

If AI-assisted or agent-proposed, summarize what the agent changed and what a human verified.

## Architectural invariants
Which invariant from `docs/architecture.md` is relevant, and how is it preserved?

## Validation
- [ ] `python -m pytest -q`
- [ ] `python -m ruff check .`
- [ ] `python -m mypy core scenarios`
- [ ] `python scripts/validate_repo.py`

## Risk, containment, rollback
Describe failure modes, containment, and how to revert this change.

## Reviewer checklist
- [ ] No secrets or generated artifacts committed
- [ ] Tests cover behavior changes
- [ ] CI evidence is green
- [ ] Human/code-owner review completed
