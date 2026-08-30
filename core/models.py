from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class ImpactDomain(str, Enum):
    SECURITY = "security"
    PRIVACY = "privacy"


class DeltaKind(str, Enum):
    NONE = "none"
    SEMANTIC = "semantic"
    CONSEQUENCE = "consequence"


class Decision(str, Enum):
    ALLOW = "ALLOW"
    ALLOW_AUDIT = "ALLOW + AUDIT"
    CONSTRAIN = "CONSTRAIN"
    REQUIRE_APPROVAL = "REQUIRE APPROVAL"
    BLOCK = "BLOCK"


@dataclass(frozen=True)
class Evidence:
    source_id: str
    domain: str
    sensitivity: int = 0  # 0=public, 1=internal, 2=confidential, 3=highly confidential / strategic
    trust: float = 1.0
    relevance: float = 1.0
    independent_group: Optional[str] = None
    summary: str = ""

    @property
    def contribution(self) -> float:
        return max(0.0, min(1.0, self.trust)) * max(0.0, min(1.0, self.relevance))


@dataclass(frozen=True)
class AgentEvent:
    step: int
    action: str
    tool: str
    description: str
    principal: str = "demo-user"
    agent_id: str = "agent-horizon-demo"
    destination: Optional[str] = None
    evidence: List[Evidence] = field(default_factory=list)
    creates_derived_knowledge: bool = False
    derived_fact: Optional[str] = None
    derived_sensitivity: int = 0
    capability_changes: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ContextualState:
    step: int = 0
    evidence: Dict[str, Evidence] = field(default_factory=dict)
    ignored_evidence: Dict[str, Evidence] = field(default_factory=dict)
    domains: Dict[str, int] = field(default_factory=dict)
    max_sensitivity: int = 0
    derived_facts: List[str] = field(default_factory=list)
    max_derived_sensitivity: int = 0
    external_destination_seen: bool = False
    trust_boundary_crossed: bool = False
    capabilities: Dict[str, Any] = field(
        default_factory=lambda: {
            "rollback_available": True,
            "reversible": True,
            "blast_radius": "low",
            "external_publish": False,
        }
    )
    relevant_event_count: int = 0
    ignored_event_count: int = 0
    last_action: str = ""
    history: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class DeltaAssessment:
    kind: DeltaKind
    score: float
    confidence: float
    impact: float
    stability: float
    reasons: List[str] = field(default_factory=list)
    impact_domains: List[ImpactDomain] = field(default_factory=list)
    slow_path_recommended: bool = False

    @property
    def effective_risk(self) -> float:
        # Bounded demo heuristic only; not intended as a production risk formula.
        return max(0.0, min(1.0, self.score * self.confidence * self.impact * self.stability))


@dataclass(frozen=True)
class PolicyDecision:
    decision: Decision
    reason: str
    assessment: DeltaAssessment
    constrained_capabilities: List[str] = field(default_factory=list)
