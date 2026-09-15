# Agent Horizon — Agentic Engineering Guide

## Mission
Agent Horizon demonstrates trajectory-aware contextual security for agentic systems.
It complements identity, authorization, MCP/A2A gateways, and point-in-time guardrails.

Core question:

> Given the trajectory so far, what does the next permitted action make newly knowable or newly possible?

## Architecture
`Agent trajectory -> structured events -> compact contextual state -> delta assessment -> policy decision`

Fast path:
- deterministic state reduction
- provenance and contribution tracking
- semantic/consequence heuristics
- policy evaluation

Slow path:
- invoked only for ambiguous or materially novel semantic changes
- mocked in the hackathon implementation so the demo stays deterministic

## Important invariants
- Do not classify every event as risky.
- Preserve provenance for contributing evidence.
- Low-contribution noise must not dominate active context.
- Semantic delta means newly derived knowledge, not merely copied sensitive text.
- Consequence delta means a meaningful change in capability, reversibility, blast radius, or impact.
- Individual authorization does not imply trajectory-level safety.

## Validate changes
Run:

```powershell
python -m pip install -r requirements.txt
pytest -q
python -m py_compile app.py core/*.py scenarios/*.py automation/*.py
```

Then smoke test:

```powershell
streamlit run app.py
```

Expected demo outcomes:
- Semantic Delta ends in `BLOCK` on external publication of a derived strategic fact.
- Consequence Delta requires approval when rollback/reversibility is lost.
- Smokescreen events remain visible in the trajectory but are excluded from active evidence.

## Safe modification strategy for AI coding agents
1. Read `core/models.py`.
2. Read `core/state_reducer.py`.
3. Read `core/delta_engine.py`.
4. Read `core/policy_engine.py`.
5. Read the scenario being changed.
6. Update or add tests before changing behavior.
7. Run the validation commands above.
8. Keep UI changes separate from core policy behavior where possible.
