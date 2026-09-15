# Copilot instructions for Agent Horizon

Treat this repository as a small security-runtime prototype, not a generic Streamlit app.

Before editing core behavior, read:
- `AGENT_READINESS.md`
- `core/models.py`
- `core/state_reducer.py`
- `core/delta_engine.py`
- `core/policy_engine.py`
- relevant files under `scenarios/` and `tests/`

Preserve the distinction between:
1. per-action identity/authorization,
2. compact trajectory context,
3. semantic delta (newly knowable),
4. consequence delta (newly possible),
5. contextual policy enforcement.

Prefer deterministic, testable logic in the fast path. Do not introduce a network dependency into core evaluation. Keep the semantic slow path optional.

After any code change run:
`pytest -q`
and:
`python -m py_compile app.py core/*.py scenarios/*.py automation/*.py`
