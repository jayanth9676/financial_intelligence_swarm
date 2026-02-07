"""Tests for LangGraph state schemas."""

from typing import get_type_hints
from backend.models.state import AgentState, DebateMessage


class TestDebateMessage:
    """Tests for DebateMessage schema."""

    def test_debate_message_fields(self):
        """Test DebateMessage has required fields."""
        hints = get_type_hints(DebateMessage)
        assert "speaker" in hints
        assert "content" in hints
        assert "evidence_ids" in hints
        assert "timestamp" in hints

    def test_debate_message_creation(self):
        """Test creating a valid DebateMessage."""
        msg: DebateMessage = {
            "speaker": "prosecutor",
            "content": "Test content",
            "evidence_ids": ["EVID-001"],
            "timestamp": "2026-02-04T10:00:00",
        }
        assert msg["speaker"] == "prosecutor"
        assert msg["content"] == "Test content"
        assert len(msg["evidence_ids"]) == 1


class TestAgentState:
    """Tests for AgentState schema."""

    def test_agent_state_has_transaction_fields(self):
        """Test AgentState has transaction context fields."""
        hints = get_type_hints(AgentState)
        assert "uetr" in hints
        assert "iso_message" in hints

    def test_agent_state_has_intelligence_scores(self):
        """Test AgentState has intelligence score fields."""
        hints = get_type_hints(AgentState)
        assert "graph_risk_score" in hints
        assert "semantic_risk_score" in hints
        assert "historical_drift" in hints

    def test_agent_state_has_debate_fields(self):
        """Test AgentState has debate trail fields."""
        hints = get_type_hints(AgentState)
        assert "prosecutor_findings" in hints
        assert "skeptic_findings" in hints
        assert "messages" in hints

    def test_agent_state_has_graph_context(self):
        """Test AgentState has graph context fields."""
        hints = get_type_hints(AgentState)
        assert "graph_context" in hints
        assert "hidden_links" in hints

    def test_agent_state_has_doc_context(self):
        """Test AgentState has document context fields."""
        hints = get_type_hints(AgentState)
        assert "doc_context" in hints
        assert "alibi_evidence" in hints

    def test_agent_state_has_memory_context(self):
        """Test AgentState has memory context fields."""
        hints = get_type_hints(AgentState)
        assert "drift_context" in hints
        assert "behavioral_baseline" in hints

    def test_agent_state_has_outcome_fields(self):
        """Test AgentState has outcome fields."""
        hints = get_type_hints(AgentState)
        assert "verdict" in hints
        assert "risk_level" in hints
        assert "confidence_score" in hints
        assert "human_override" in hints

    def test_agent_state_has_control_flow(self):
        """Test AgentState has control flow fields."""
        hints = get_type_hints(AgentState)
        assert "current_phase" in hints
        assert "round_count" in hints
        assert "needs_more_evidence" in hints

    def test_agent_state_list_fields_have_reducers(self):
        """Test that list fields use Annotated with reducers for LangGraph."""
        from typing import Annotated, get_origin

        hints = get_type_hints(AgentState, include_extras=True)

        # Check prosecutor_findings has Annotated type (reducer)
        prosecutor_type = hints.get("prosecutor_findings")
        assert get_origin(prosecutor_type) is Annotated

        # Check skeptic_findings has Annotated type (reducer)
        skeptic_type = hints.get("skeptic_findings")
        assert get_origin(skeptic_type) is Annotated

        # Check messages has Annotated type (reducer)
        messages_type = hints.get("messages")
        assert get_origin(messages_type) is Annotated


class TestAgentStateCreation:
    """Tests for creating AgentState instances."""

    def test_create_minimal_agent_state(self):
        """Test creating AgentState with minimal fields."""
        state: AgentState = {
            "uetr": "test-uetr",
            "iso_message": {},
            "graph_risk_score": 0.0,
            "semantic_risk_score": 0.5,
            "historical_drift": 0.0,
            "prosecutor_findings": [],
            "skeptic_findings": [],
            "messages": [],
            "graph_context": "",
            "hidden_links": [],
            "doc_context": "",
            "alibi_evidence": [],
            "drift_context": "",
            "behavioral_baseline": {},
            "verdict": None,
            "risk_level": "medium",
            "confidence_score": 0.0,
            "human_override": None,
            "current_phase": "investigation",
            "round_count": 1,
            "needs_more_evidence": False,
        }
        assert state["uetr"] == "test-uetr"
        assert state["risk_level"] == "medium"
        assert state["round_count"] == 1
