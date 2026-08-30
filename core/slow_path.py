from __future__ import annotations

from dataclasses import replace

from .models import DeltaAssessment, DeltaKind


def mock_semantic_reassessment(assessment: DeltaAssessment) -> DeltaAssessment:
    """Deterministic stand-in for a future LLM/classifier slow path.

    This intentionally performs no external call. It lets the demo show where a
    model-assisted evaluator would plug in without making the prototype network-dependent.
    """
    if assessment.kind != DeltaKind.SEMANTIC:
        return assessment

    reasons = list(assessment.reasons)
    reasons.append("Slow-path semantic reassessment confirmed the inference is materially novel relative to individual sources.")
    return replace(
        assessment,
        confidence=max(assessment.confidence, 0.90),
        stability=max(assessment.stability, 0.85),
        reasons=reasons,
        slow_path_recommended=False,
    )
