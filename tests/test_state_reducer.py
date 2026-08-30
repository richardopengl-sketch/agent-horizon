from core.models import ContextualState
from core.state_reducer import reduce_state
from scenarios.semantic_delta import build_semantic_delta_scenario


def test_smokescreen_is_ignored():
    state = ContextualState()
    events = build_semantic_delta_scenario(include_smokescreen=True)
    for event in events[:4]:
        _, state = reduce_state(state, event)
    assert state.relevant_event_count == 2
    assert state.ignored_event_count == 2
    assert "PublicWeather" not in state.domains
