from core.delta_engine import assess_delta
from core.models import ContextualState, DeltaKind
from core.policy_engine import evaluate_policy
from core.state_reducer import reduce_state
from scenarios.semantic_delta import build_semantic_delta_scenario


def test_semantic_delta_emerges_after_correlation():
    state = ContextualState()
    assessment = None
    events = build_semantic_delta_scenario(include_smokescreen=False)
    for event in events:
        before, after = reduce_state(state, event)
        current = assess_delta(before, after, event)
        if event.action == "infer":
            assessment = current
        state = after
    assert assessment is not None
    assert assessment.kind == DeltaKind.SEMANTIC
    assert assessment.score >= 0.65


def test_external_publish_blocks_derived_sensitive_context():
    state = ContextualState()
    semantic = None
    events = build_semantic_delta_scenario(include_smokescreen=False)
    for event in events:
        before, after = reduce_state(state, event)
        current = assess_delta(before, after, event)
        if current.kind == DeltaKind.SEMANTIC:
            semantic = current
        state = after
    assert semantic is not None
    decision = evaluate_policy(state, semantic, "publish_external")
    assert decision.decision.value == "BLOCK"
