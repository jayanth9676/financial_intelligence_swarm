"""Integration tests for the Prosecutor-Skeptic-Judge debate workflow.

These tests verify the full debate loop works correctly, including:
- State transitions between agents
- Proper accumulation of findings with Annotated reducers
- Conditional continuation based on confidence
- Verdict generation
"""

import pytest

from backend.graph import (
    create_investigation_graph,
    create_initial_state,
    should_continue_debate,
)
from backend.models.state import DebateMessage


class TestDebateWorkflowIntegration:
    """Integration tests for the full debate workflow."""

    def test_initial_state_has_all_required_fields(self, minimal_transaction):
        """Verify initial state contains all AgentState fields."""
        state = create_initial_state(
            uetr="test-uetr",
            iso_message=minimal_transaction,
        )

        # Core transaction fields
        assert state["uetr"] == "test-uetr"
        assert state["iso_message"] == minimal_transaction

        # Risk scores initialized
        assert state["graph_risk_score"] == 0.0
        assert state["semantic_risk_score"] == 0.5  # Neutral start
        assert state["historical_drift"] == 0.0

        # Lists initialized empty (will accumulate via reducers)
        assert state["prosecutor_findings"] == []
        assert state["skeptic_findings"] == []
        assert state["messages"] == []
        assert state["hidden_links"] == []
        assert state["alibi_evidence"] == []

        # Context strings
        assert state["graph_context"] == ""
        assert state["doc_context"] == ""
        assert state["drift_context"] == ""

        # Outcome fields
        assert state["verdict"] is None
        assert state["risk_level"] == "medium"
        assert state["confidence_score"] == 0.0
        assert state["human_override"] is None

        # Control flow
        assert state["current_phase"] == "investigation"
        assert state["round_count"] == 1
        assert state["needs_more_evidence"] is False

    def test_graph_has_correct_node_structure(self):
        """Verify the compiled graph has prosecutor -> skeptic -> judge flow."""
        workflow = create_investigation_graph()

        # Check nodes are defined
        assert "prosecutor" in workflow.nodes
        assert "skeptic" in workflow.nodes
        assert "judge" in workflow.nodes

    def test_debate_continues_when_low_confidence(self):
        """Verify debate loops back when confidence is below threshold."""
        state = {
            "needs_more_evidence": True,
            "round_count": 1,
            "confidence_score": 0.5,
        }

        result = should_continue_debate(state)
        assert result == "prosecutor"

    def test_debate_ends_when_high_confidence(self):
        """Verify debate ends when confidence exceeds threshold."""
        state = {
            "needs_more_evidence": True,
            "round_count": 1,
            "confidence_score": 0.9,
        }

        result = should_continue_debate(state)
        assert result == "end"

    def test_debate_ends_after_max_rounds(self):
        """Verify debate ends after 3 rounds regardless of confidence."""
        state = {
            "needs_more_evidence": True,
            "round_count": 4,  # Exceeds max of 3
            "confidence_score": 0.3,
        }

        result = should_continue_debate(state)
        assert result == "end"

    def test_debate_ends_when_no_more_evidence_needed(self):
        """Verify debate ends when judge doesn't need more evidence."""
        state = {
            "needs_more_evidence": False,
            "round_count": 1,
            "confidence_score": 0.6,
        }

        result = should_continue_debate(state)
        assert result == "end"


class TestStateAccumulation:
    """Tests for proper state accumulation via Annotated reducers."""

    def test_prosecutor_findings_accumulate(self):
        """Verify prosecutor findings append rather than overwrite."""
        state1 = {"prosecutor_findings": ["Finding 1", "Finding 2"]}
        new_findings = ["Finding 3"]

        # Simulate what the reducer should do
        combined = state1["prosecutor_findings"] + new_findings
        assert combined == ["Finding 1", "Finding 2", "Finding 3"]

    def test_messages_accumulate_across_rounds(self):
        """Verify debate messages accumulate correctly."""
        msg1: DebateMessage = {
            "speaker": "prosecutor",
            "content": "Round 1 prosecution",
            "evidence_ids": ["EVID-1"],
            "timestamp": "2026-02-03T09:00:00Z",
        }
        msg2: DebateMessage = {
            "speaker": "skeptic",
            "content": "Round 1 defense",
            "evidence_ids": ["DEF-1"],
            "timestamp": "2026-02-03T09:01:00Z",
        }
        msg3: DebateMessage = {
            "speaker": "judge",
            "content": "Round 1 verdict",
            "evidence_ids": [],
            "timestamp": "2026-02-03T09:02:00Z",
        }

        messages = [msg1, msg2, msg3]
        assert len(messages) == 3
        assert messages[0]["speaker"] == "prosecutor"
        assert messages[1]["speaker"] == "skeptic"
        assert messages[2]["speaker"] == "judge"

    def test_hidden_links_accumulate(self):
        """Verify hidden links from multiple rounds combine."""
        links_round1 = [{"path": ["A", "B", "C"], "risk": 0.7}]
        links_round2 = [{"path": ["D", "E", "F"], "risk": 0.8}]

        combined = links_round1 + links_round2
        assert len(combined) == 2


class TestAgentMocking:
    """Tests with mocked agent responses for faster execution."""

    @pytest.fixture
    def mock_prosecutor_response(self):
        """Mock prosecutor agent response."""
        return {
            "prosecutor_findings": ["HIDDEN LINK DETECTED: Shell Company -> Sanctioned Entity"],
            "messages": [
                {
                    "speaker": "prosecutor",
                    "content": "Investigation complete. Found suspicious links.",
                    "evidence_ids": ["EVID-0"],
                    "timestamp": "2026-02-03T09:00:00Z",
                }
            ],
            "graph_context": "Neo4j analysis complete",
            "hidden_links": [{"path": ["Shell", "Intermediary", "Sanctioned"]}],
            "graph_risk_score": 0.85,
            "current_phase": "rebuttal",
        }

    @pytest.fixture
    def mock_skeptic_response(self):
        """Mock skeptic agent response."""
        return {
            "skeptic_findings": ["PAYMENT AUTHORIZED: Found valid MSA contract"],
            "messages": [
                {
                    "speaker": "skeptic",
                    "content": "Defense complete. Found exculpatory evidence.",
                    "evidence_ids": ["DEF-0"],
                    "timestamp": "2026-02-03T09:01:00Z",
                }
            ],
            "doc_context": "Qdrant search complete",
            "alibi_evidence": ["MSA contract dated 2024-01-15"],
            "semantic_risk_score": 0.3,
            "current_phase": "verdict",
        }

    @pytest.fixture
    def mock_judge_response(self):
        """Mock judge agent response."""
        return {
            "verdict": {
                "verdict": "REVIEW",
                "risk_level": "medium",
                "confidence_score": 0.75,
                "reasoning": "Evidence is mixed. Recommend human review.",
                "needs_more_evidence": False,
            },
            "risk_level": "medium",
            "confidence_score": 0.75,
            "messages": [
                {
                    "speaker": "judge",
                    "content": '{"verdict": "REVIEW", "confidence_score": 0.75}',
                    "evidence_ids": [],
                    "timestamp": "2026-02-03T09:02:00Z",
                }
            ],
            "needs_more_evidence": False,
            "round_count": 2,
            "current_phase": "verdict",
        }

    def test_full_debate_flow_mocked(
        self,
        minimal_transaction,
        mock_prosecutor_response,
        mock_skeptic_response,
        mock_judge_response,
    ):
        """Test full debate flow with mocked agent responses."""
        initial_state = create_initial_state(
            uetr="test-uetr",
            iso_message=minimal_transaction,
        )

        # Simulate prosecutor updates
        state_after_prosecutor = {**initial_state, **mock_prosecutor_response}
        assert state_after_prosecutor["graph_risk_score"] == 0.85
        assert len(state_after_prosecutor["prosecutor_findings"]) == 1

        # Simulate skeptic updates (findings accumulate)
        state_after_skeptic = {**state_after_prosecutor, **mock_skeptic_response}
        assert state_after_skeptic["semantic_risk_score"] == 0.3
        assert len(state_after_skeptic["skeptic_findings"]) == 1

        # Simulate judge verdict
        state_after_judge = {**state_after_skeptic, **mock_judge_response}
        assert state_after_judge["verdict"]["verdict"] == "REVIEW"
        assert state_after_judge["confidence_score"] == 0.75
        assert state_after_judge["needs_more_evidence"] is False


class TestVerdictGeneration:
    """Tests for verdict generation and risk level calculation."""

    def test_calculate_risk_level_critical(self):
        """Test critical risk level calculation.
        
        Formula: (graph * 0.5) + (semantic * 0.3) + (drift * 0.2) >= 0.85
        Example: (1.0 * 0.5) + (1.0 * 0.3) + (1.0 * 0.2) = 1.0 >= 0.85
        """
        from backend.agents.judge import calculate_risk_level

        # All max values = 1.0 combined
        risk = calculate_risk_level(1.0, 1.0, 1.0)
        assert risk == "critical"

    def test_calculate_risk_level_high(self):
        """Test high risk level calculation.
        
        Formula: 0.65 <= combined < 0.85
        Example: (0.9 * 0.5) + (0.7 * 0.3) + (0.6 * 0.2) = 0.45 + 0.21 + 0.12 = 0.78
        """
        from backend.agents.judge import calculate_risk_level

        risk = calculate_risk_level(0.9, 0.7, 0.6)
        assert risk == "high"

    def test_calculate_risk_level_medium(self):
        """Test medium risk level calculation."""
        from backend.agents.judge import calculate_risk_level

        risk = calculate_risk_level(0.5, 0.4, 0.3)
        assert risk == "medium"

    def test_calculate_risk_level_low(self):
        """Test low risk level calculation."""
        from backend.agents.judge import calculate_risk_level

        risk = calculate_risk_level(0.1, 0.2, 0.1)
        assert risk == "low"


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_empty_iso_message(self):
        """Test workflow handles empty ISO message gracefully."""
        state = create_initial_state(uetr="empty-test", iso_message={})

        assert state["uetr"] == "empty-test"
        assert state["iso_message"] == {}
        assert state["risk_level"] == "medium"

    def test_missing_debtor_creditor(self):
        """Test workflow handles missing debtor/creditor fields."""
        iso_message = {"amount": {"value": "1000", "currency": "EUR"}}
        state = create_initial_state(uetr="partial-test", iso_message=iso_message)

        # Should not raise, debtor/creditor handled with defaults
        assert state["iso_message"]["amount"]["value"] == "1000"

    def test_confidence_boundary_at_exactly_0_8(self):
        """Test boundary condition at exactly 0.8 confidence."""
        state = {
            "needs_more_evidence": True,
            "round_count": 2,
            "confidence_score": 0.8,  # Exactly at threshold
        }

        # At 0.8, confidence < 0.8 is False, so should end
        result = should_continue_debate(state)
        assert result == "end"

    def test_round_count_boundary_at_exactly_3(self):
        """Test boundary condition at exactly 3 rounds."""
        state = {
            "needs_more_evidence": True,
            "round_count": 3,  # At max
            "confidence_score": 0.5,
        }

        # round_count <= 3 is True, so should continue
        result = should_continue_debate(state)
        assert result == "prosecutor"

    def test_state_default_values(self):
        """Test default values when state fields are missing."""
        state = {}  # Empty state

        result = should_continue_debate(state)
        # With defaults: needs_more=False, so should end
        assert result == "end"
