"""LangGraph state schemas for the Financial Intelligence Swarm."""

from operator import add
from typing import Annotated, Any, Dict, List, Literal, Optional, TypedDict


class DebateMessage(TypedDict):
    """A message in the Prosecutor-Skeptic-Judge debate."""

    speaker: Literal["prosecutor", "skeptic", "judge"]
    content: str
    evidence_ids: List[str]
    timestamp: str


class ToolCall(TypedDict):
    """Record of a tool execution by an agent."""

    agent: str
    tool_name: str
    tool_args: Dict[str, Any]
    result: str  # Stringified result for display
    timestamp: str


def merge_lists(left: List, right: List) -> List:
    """Reducer that merges lists, avoiding duplicates where possible."""
    return left + right


class AgentState(TypedDict):
    """Shared state for the investigation workflow.

    Uses Annotated types with reducers for list fields to ensure proper
    state merging across debate rounds in LangGraph.
    """

    # Transaction Context (immutable during investigation)
    uetr: str
    iso_message: Dict[str, Any]

    # Intelligence Scores (updated by agents)
    graph_risk_score: float
    semantic_risk_score: float
    historical_drift: float

    # Debate Trail (use reducers to append, not overwrite)
    prosecutor_findings: Annotated[List[str], add]
    skeptic_findings: Annotated[List[str], add]
    messages: Annotated[List[DebateMessage], add]
    tool_calls: Annotated[List[ToolCall], add]

    # Graph Context (Neo4j results)
    graph_context: str
    hidden_links: Annotated[List[Dict[str, Any]], add]

    # Document Context (Qdrant results)
    doc_context: str
    alibi_evidence: Annotated[List[str], add]

    # Memory Context (Mem0 results)
    drift_context: str
    behavioral_baseline: Dict[str, Any]

    # Outcome
    verdict: Optional[Dict[str, Any]]
    risk_level: Literal["low", "medium", "high", "critical"]
    confidence_score: float
    human_override: Optional[bool]

    # Control Flow
    current_phase: Literal["investigation", "rebuttal", "verdict"]
    round_count: int
    needs_more_evidence: bool
