from core.models import (
    AgentEvent,
    ContextualState,
    Decision,
    DeltaAssessment,
    DeltaKind,
    Evidence,
    ImpactDomain,
)


def test_contextual_state_starts_reversible_and_internal():
    state = ContextualState()
    assert state.capabilities["rollback_available"] is True
    assert state.capabilities["reversible"] is True
    assert state.capabilities["external_publish"] is False
    assert state.trust_boundary_crossed is False


def test_evidence_contribution_is_bounded():
    high = Evidence(source_id="high", domain="demo", trust=2.0, relevance=4.0)
    low = Evidence(source_id="low", domain="demo", trust=-1.0, relevance=1.0)
    assert high.contribution == 1.0
    assert low.contribution == 0.0


def test_effective_risk_is_bounded():
    assessment = DeltaAssessment(
        kind=DeltaKind.SEMANTIC,
        score=2.0,
        confidence=2.0,
        impact=2.0,
        stability=2.0,
        reasons=["test"],
        impact_domains=[ImpactDomain.SECURITY],
    )
    assert assessment.effective_risk == 1.0


def test_decision_vocabulary_preserves_human_approval_state():
    assert Decision.REQUIRE_APPROVAL.value == "REQUIRE APPROVAL"


def test_agent_event_defaults_do_not_cross_boundary():
    event = AgentEvent(step=1, action="read", tool="demo", description="read an internal source")
    assert event.destination is None
    assert event.creates_derived_knowledge is False
    assert event.capability_changes == {}
