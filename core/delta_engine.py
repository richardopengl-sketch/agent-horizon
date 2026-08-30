from __future__ import annotations

from typing import List

from .models import AgentEvent, ContextualState, DeltaAssessment, DeltaKind, ImpactDomain


def _independent_evidence_groups(state: ContextualState) -> int:
    return len({ev.independent_group or ev.source_id for ev in state.evidence.values()})


def _semantic_delta(before: ContextualState, after: ContextualState, event: AgentEvent) -> DeltaAssessment:
    if not event.creates_derived_knowledge:
        return DeltaAssessment(
            kind=DeltaKind.NONE,
            score=0.0,
            confidence=1.0,
            impact=0.0,
            stability=1.0,
            reasons=["No new derived knowledge was created."],
        )

    groups = _independent_evidence_groups(after)
    high_trust = [e for e in after.evidence.values() if e.trust >= 0.75 and e.relevance >= 0.6]
    relevant_domains = {e.domain for e in high_trust}

    reasons: List[str] = []
    score = 0.25
    confidence = 0.55
    impact = 0.45
    stability = 0.65

    if groups >= 2:
        score += 0.20
        confidence += 0.10
        reasons.append(f"Inference combines {groups} independent evidence groups.")

    if len(relevant_domains) >= 2:
        score += 0.15
        confidence += 0.10
        reasons.append(f"Evidence crosses {len(relevant_domains)} relevant domains.")

    sensitivity_uplift = max(0, event.derived_sensitivity - after.max_sensitivity)
    if sensitivity_uplift > 0:
        score += min(0.20, 0.10 * sensitivity_uplift)
        impact += min(0.40, 0.20 * sensitivity_uplift)
        reasons.append(
            f"Derived knowledge sensitivity rises above any individual source "
            f"({after.max_sensitivity} → {event.derived_sensitivity})."
        )
    elif after.max_sensitivity >= 2:
        impact += 0.20
    elif after.max_sensitivity >= 1:
        impact += 0.10

    if len(high_trust) >= 3:
        confidence += 0.10
        stability += 0.15
        reasons.append("Inference is supported by multiple high-trust, high-relevance sources.")

    if after.ignored_event_count > 0:
        stability += 0.05
        reasons.append(f"{after.ignored_event_count} low-contribution event(s) were ignored as smokescreen/noise.")

    if event.metadata.get("material_novelty", False):
        impact += 0.10
        reasons.append("The conclusion is materially novel: it was not explicit in any single source.")

    # Semantic novelty/sensitivity is exactly where a model-assisted reassessment
    # can add value. The deterministic reducer decides when to invoke it.
    explicit_semantic_review = bool(event.metadata.get("requires_semantic_review", False))

    return DeltaAssessment(
        kind=DeltaKind.SEMANTIC,
        score=min(score, 1.0),
        confidence=min(confidence, 1.0),
        impact=min(impact, 1.0),
        stability=min(stability, 1.0),
        reasons=reasons or ["New derived knowledge was created from prior evidence."],
        impact_domains=[ImpactDomain.SECURITY],
        slow_path_recommended=explicit_semantic_review or confidence < 0.80 or stability < 0.75,
    )


def _consequence_delta(before: ContextualState, after: ContextualState, event: AgentEvent) -> DeltaAssessment:
    reasons: List[str] = []
    score = 0.0
    impact = 0.0
    confidence = 0.95
    stability = 0.95

    before_reversible = bool(before.capabilities.get("reversible", True))
    after_reversible = bool(after.capabilities.get("reversible", True))
    if before_reversible and not after_reversible:
        score += 0.65
        impact += 0.75
        reasons.append("System transitions from reversible to effectively irreversible.")

    before_rollback = bool(before.capabilities.get("rollback_available", True))
    after_rollback = bool(after.capabilities.get("rollback_available", True))
    if before_rollback and not after_rollback:
        score += 0.30
        impact += 0.20
        reasons.append("Rollback capability is removed.")

    before_blast = str(before.capabilities.get("blast_radius", "low"))
    after_blast = str(after.capabilities.get("blast_radius", "low"))
    rank = {"low": 0, "medium": 1, "high": 2, "production": 3}
    if rank.get(after_blast, 0) > rank.get(before_blast, 0):
        score += 0.15
        impact += 0.15
        reasons.append(f"Blast radius increases from {before_blast} to {after_blast}.")

    if not reasons:
        return DeltaAssessment(
            kind=DeltaKind.NONE,
            score=0.0,
            confidence=1.0,
            impact=0.0,
            stability=1.0,
            reasons=["No material consequence transition detected."],
        )

    return DeltaAssessment(
        kind=DeltaKind.CONSEQUENCE,
        score=min(score, 1.0),
        confidence=confidence,
        impact=min(impact, 1.0),
        stability=stability,
        reasons=reasons,
        impact_domains=[ImpactDomain.SECURITY],
        slow_path_recommended=False,
    )


def assess_delta(before: ContextualState, after: ContextualState, event: AgentEvent) -> DeltaAssessment:
    """Assess the most material contextual delta introduced by this event."""
    consequence = _consequence_delta(before, after, event)
    semantic = _semantic_delta(before, after, event)

    candidates = [a for a in (semantic, consequence) if a.kind != DeltaKind.NONE]
    if not candidates:
        return DeltaAssessment(
            kind=DeltaKind.NONE,
            score=0.0,
            confidence=1.0,
            impact=0.0,
            stability=1.0,
            reasons=["Event is individually permitted and creates no material contextual delta."],
        )

    return max(candidates, key=lambda a: (a.score * a.impact, a.confidence))
