# Agentic Engineering Loop

This repository supports AI-assisted engineering while keeping deterministic validation and human review as control boundaries.

```text
Issue / request
  -> agent or human proposes bounded change
  -> local validation
  -> pull request
  -> CI emits machine-readable evidence
  -> human/code-owner review
  -> merge
  -> scheduled maintenance revalidates repository health
```

## Agent contract

1. Read `.github/copilot-instructions.md` and `docs/architecture.md`.
2. Identify the smallest relevant component.
3. Preserve architectural invariants.
4. Run `python scripts/validate_repo.py`.
5. Report exact pass/fail evidence.
6. Never weaken tests or trust-boundary behavior merely to make CI green.
7. Stop for human review before merge/deployment.

The canonical completion signal is `.reports/validation-report.json` with `"ok": true`.
