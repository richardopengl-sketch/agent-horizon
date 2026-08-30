from core.delta_engine import assess_delta
from core.models import ContextualState, DeltaKind
from core.policy_engine import evaluate_policy
from core.state_reducer import reduce_state
from scenarios.consequence_delta import build_consequence_delta_scenario


def test_delete_rollback_creates_high_consequence_delta():
    state = ContextualState()
    final_assessment = None
    final_event = None
    for event in build_consequence_delta_scenario():
        before, after = reduce_state(state, event)
        assessment = assess_delta(before, after, event)
        state = after
        final_assessment = assessment
        final_event = event

    assert final_assessment is not None
    assert final_assessment.kind == DeltaKind.CONSEQUENCE
    assert final_assessment.impact >= 0.75
    decision = evaluate_policy(state, final_assessment, final_event.action)
    assert decision.decision.value == "REQUIRE APPROVAL"
