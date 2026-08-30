from __future__ import annotations

from .models import ContextualState, Decision, DeltaAssessment, DeltaKind, PolicyDecision


def evaluate_policy(state: ContextualState, assessment: DeltaAssessment, requested_action: str) -> PolicyDecision:
    """Demo policy: use contextual impact, not content matching, as the decision primitive."""
    action = requested_action.lower()
    external_or_destructive = any(
        token in action
        for token in ("publish", "external", "send", "delete", "disable", "commit", "execute")
    )

    if assessment.kind == DeltaKind.NONE:
        return PolicyDecision(
            decision=Decision.ALLOW,
            reason="No material contextual delta detected.",
            assessment=assessment,
        )

    if assessment.kind == DeltaKind.CONSEQUENCE:
        if assessment.impact >= 0.75 and external_or_destructive:
            return PolicyDecision(
                decision=Decision.REQUIRE_APPROVAL,
                reason="The requested action crosses a high-impact consequence boundary and requires human approval.",
                assessment=assessment,
                constrained_capabilities=["irreversible operations"],
            )
        return PolicyDecision(
            decision=Decision.ALLOW_AUDIT,
            reason="Consequence delta detected but below the blocking threshold.",
            assessment=assessment,
        )

    if assessment.kind == DeltaKind.SEMANTIC:
        if state.external_destination_seen and assessment.score >= 0.65:
            return PolicyDecision(
                decision=Decision.BLOCK,
                reason="Newly derived sensitive context would cross an external trust boundary.",
                assessment=assessment,
                constrained_capabilities=["external publishing", "external messaging"],
            )
        if assessment.slow_path_recommended:
            return PolicyDecision(
                decision=Decision.CONSTRAIN,
                reason="Semantic delta is material but uncertain; continue analysis internally while constraining external actions.",
                assessment=assessment,
                constrained_capabilities=["external publishing"],
            )
        return PolicyDecision(
            decision=Decision.REQUIRE_APPROVAL,
            reason="Material semantic delta detected; require approval before high-impact use.",
            assessment=assessment,
        )

    return PolicyDecision(
        decision=Decision.ALLOW_AUDIT,
        reason="Default audit path.",
        assessment=assessment,
    )
