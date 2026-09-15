from __future__ import annotations

from copy import deepcopy
from typing import Tuple

from .models import AgentEvent, ContextualState, Evidence

RELEVANCE_THRESHOLD = 0.35


def _is_relevant(evidence: Evidence) -> bool:
    return evidence.contribution >= RELEVANCE_THRESHOLD


def reduce_state(state: ContextualState, event: AgentEvent) -> Tuple[ContextualState, ContextualState]:
    """Return (before, after) for one structured agent event.

    The runtime reducer keeps only compact security/privacy context and provenance
    metadata. Raw content is not required for the deterministic fast path.
    """
    before = deepcopy(state)
    after = deepcopy(state)
    after.step = event.step
    after.last_action = event.action
    after.history.append(f"{event.step}. {event.action}: {event.description}")

    for ev in event.evidence:
        if _is_relevant(ev):
            after.evidence[ev.source_id] = ev
            after.domains[ev.domain] = after.domains.get(ev.domain, 0) + 1
            after.max_sensitivity = max(after.max_sensitivity, ev.sensitivity)
            after.relevant_event_count += 1
        else:
            after.ignored_evidence[ev.source_id] = ev
            after.ignored_event_count += 1

    if event.creates_derived_knowledge and event.derived_fact:
        after.derived_facts.append(event.derived_fact)
        after.max_derived_sensitivity = max(after.max_derived_sensitivity, event.derived_sensitivity)

    if event.destination:
        normalized = event.destination.lower()
        is_external = any(k in normalized for k in ("external", "public", "internet", "gmail.com", "third-party"))
        after.external_destination_seen = after.external_destination_seen or is_external
        after.trust_boundary_crossed = after.trust_boundary_crossed or is_external

    for key, value in event.capability_changes.items():
        after.capabilities[key] = value

    return before, after
