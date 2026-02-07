"""Tests for LangGraph workflow and graph module."""

from backend.graph import (
    create_investigation_graph,
    create_initial_state,
    get_compiled_graph,
    should_continue_debate,
)


class TestCreateInitialState:
    """Tests for initial state creation."""

    def test_create_initial_state_basic(self):
        """Test creating initial state with basic inputs."""
        uetr = "test-uetr-12345"
        iso_message = {
            "debtor": {"name": "Test Debtor"},
            "creditor": {"name": "Test Creditor"},
            "amount": {"value": "1000", "currency": "EUR"},
        }

        state = create_initial_state(uetr, iso_message)

        assert state["uetr"] == uetr
        assert state["iso_message"] == iso_message
        assert state["graph_risk_score"] == 0.0
        assert state["semantic_risk_score"] == 0.5
        assert state["historical_drift"] == 0.0
        assert state["prosecutor_findings"] == []
        assert state["skeptic_findings"] == []
        assert state["messages"] == []
        assert state["risk_level"] == "medium"
        assert state["confidence_score"] == 0.0
        assert state["current_phase"] == "investigation"
        assert state["round_count"] == 1
        assert state["needs_more_evidence"] is False

    def test_create_initial_state_empty_iso(self):
        """Test creating initial state with empty ISO message."""
        state = create_initial_state("empty-uetr", {})

        assert state["uetr"] == "empty-uetr"
        assert state["iso_message"] == {}


class TestShouldContinueDebate:
    """Tests for debate continuation logic."""

    def test_should_stop_when_no_more_evidence_needed(self):
        """Test debate stops when no more evidence needed."""
        state = {
            "needs_more_evidence": False,
            "round_count": 1,
            "confidence_score": 0.9,
        }
        result = should_continue_debate(state)
        assert result == "end"

    def test_should_stop_when_max_rounds_reached(self):
        """Test debate stops after max rounds."""
        state = {
            "needs_more_evidence": True,
            "round_count": 4,  # Exceeds max of 3
            "confidence_score": 0.5,
        }
        result = should_continue_debate(state)
        assert result == "end"

    def test_should_stop_when_high_confidence(self):
        """Test debate stops when confidence is high."""
        state = {
            "needs_more_evidence": True,
            "round_count": 1,
            "confidence_score": 0.9,  # Above 0.8 threshold
        }
        result = should_continue_debate(state)
        assert result == "end"

    def test_should_continue_when_low_confidence_and_rounds_left(self):
        """Test debate continues when confidence low and rounds available."""
        state = {
            "needs_more_evidence": True,
            "round_count": 2,
            "confidence_score": 0.5,
        }
        result = should_continue_debate(state)
        assert result == "prosecutor"


class TestCreateInvestigationGraph:
    """Tests for graph creation."""

    def test_create_graph_returns_state_graph(self):
        """Test that create_investigation_graph returns a StateGraph."""
        from langgraph.graph import StateGraph

        workflow = create_investigation_graph()
        assert isinstance(workflow, StateGraph)

    def test_compiled_graph_has_nodes(self):
        """Test compiled graph has expected nodes."""
        graph = get_compiled_graph()
        # Check the graph can be invoked (basic sanity check)
        assert graph is not None
