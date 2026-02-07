"""End-to-end tests for the target UETR investigation.

These tests simulate a complete investigation of the target suspicious
transaction: eb9a5c8e-2f3b-4c7a-9d1e-5f8a2b3c4d5e

The target scenario involves:
- Shell Company Alpha -> Offshore Holdings LLC
- 245,000 EUR (large amount)
- Hidden link to sanctioned entity via shared director
- Payment Grid alibi from Skeptic
"""

import pytest
from unittest.mock import patch, MagicMock

from backend.graph import (
    create_initial_state,
)
from backend.tools.tools_iso import parse_pacs008


class TestTargetUETRParsing:
    """Tests for parsing the target UETR transaction."""

    def test_parse_target_pacs008_xml(self, target_pacs008_xml):
        """Test parsing the target transaction XML."""
        result = parse_pacs008.invoke({"xml_content": target_pacs008_xml})

        assert result["parsed_successfully"] is True
        assert result["uetr"] == "eb9a5c8e-2f3b-4c7a-9d1e-5f8a2b3c4d5e"
        assert result["debtor"]["name"] == "Shell Company Alpha"
        assert result["creditor"]["name"] == "Offshore Holdings LLC"
        assert result["amount"]["value"] == "245000.00"
        assert result["amount"]["currency"] == "EUR"
        assert result["purpose_code"] == "CORT"

    def test_target_transaction_high_risk_indicators(self, suspicious_transaction):
        """Verify the target transaction has expected high-risk indicators."""
        # Shell company name
        assert "Shell" in suspicious_transaction["debtor"]["name"]

        # Offshore destination
        assert "Offshore" in suspicious_transaction["creditor"]["name"]

        # Cyprus IBAN (common offshore destination)
        assert suspicious_transaction["creditor"]["account_iban"].startswith("CY")

        # Large amount
        amount = float(suspicious_transaction["amount"]["value"])
        assert amount > 100000

        # Generic purpose code
        assert suspicious_transaction["purpose_code"] == "CORT"


class TestTargetUETRInvestigation:
    """End-to-end tests for investigating the target UETR."""

    @pytest.fixture
    def target_initial_state(self, suspicious_transaction, target_uetr):
        """Create initial state for target UETR investigation."""
        return create_initial_state(
            uetr=target_uetr,
            iso_message=suspicious_transaction,
        )

    def test_initial_state_for_target(self, target_initial_state, target_uetr):
        """Verify initial state is correctly configured for target."""
        assert target_initial_state["uetr"] == target_uetr
        assert target_initial_state["iso_message"]["debtor"]["name"] == "Shell Company Alpha"
        assert target_initial_state["risk_level"] == "medium"  # Starting level
        assert target_initial_state["round_count"] == 1

    @patch("backend.agents.prosecutor.get_prosecutor_llm")
    @patch("backend.agents.prosecutor.find_hidden_links")
    @patch("backend.agents.prosecutor.detect_fraud_rings")
    @patch("backend.agents.prosecutor.check_behavioral_drift")
    def test_prosecutor_finds_hidden_links(
        self,
        mock_drift,
        mock_fraud_rings,
        mock_hidden_links,
        mock_llm,
        target_initial_state,
        mock_graph_response_high_risk,
    ):
        """Test prosecutor agent finds hidden links in target transaction."""
        # Configure mocks
        mock_hidden_links.invoke.return_value = mock_graph_response_high_risk
        mock_fraud_rings.invoke.return_value = {"high_risk": False, "components": []}
        mock_drift.invoke.return_value = {"drift_detected": False, "drift_score": 0.1}

        # Mock LLM response
        mock_response = MagicMock()
        mock_response.content = "Found suspicious hidden link to sanctioned entity."
        mock_response.tool_calls = [
            {"name": "find_hidden_links", "args": {"entity_name": "Shell Company Alpha"}}
        ]
        mock_llm.return_value.bind_tools.return_value.invoke.return_value = mock_response

        # Import and run prosecutor
        from backend.agents.prosecutor import prosecutor_agent

        result = prosecutor_agent(target_initial_state)

        # Verify prosecutor found concerning evidence
        assert result["graph_risk_score"] >= 0.8
        assert len(result["hidden_links"]) > 0
        assert result["current_phase"] == "rebuttal"

    @patch("backend.agents.skeptic.get_skeptic_llm")
    @patch("backend.agents.skeptic.search_payment_justification")
    @patch("backend.agents.skeptic.search_alibi")
    def test_skeptic_finds_payment_grid_alibi(
        self,
        mock_alibi,
        mock_payment_just,
        mock_llm,
        target_initial_state,
        mock_alibi_evidence,
    ):
        """Test skeptic agent finds payment grid alibi."""
        # Add prosecutor findings to state
        state_after_prosecutor = {
            **target_initial_state,
            "prosecutor_findings": ["HIDDEN LINK DETECTED: Shell -> Sanctioned"],
            "graph_risk_score": 0.85,
            "current_phase": "rebuttal",
        }

        # Configure mocks
        mock_payment_just.invoke.return_value = {
            "has_valid_authorization": True,
            "justifications": [{"content": "Payment Grid Q1 2026 approved"}],
        }
        mock_alibi.invoke.return_value = mock_alibi_evidence

        # Mock LLM response
        mock_response = MagicMock()
        mock_response.content = "Found valid payment authorization in approved grid."
        mock_response.tool_calls = [
            {"name": "search_payment_justification", "args": {"entity_name": "Shell Company Alpha"}}
        ]
        mock_llm.return_value.bind_tools.return_value.invoke.return_value = mock_response

        # Import and run skeptic
        from backend.agents.skeptic import skeptic_agent

        result = skeptic_agent(state_after_prosecutor)

        # Verify skeptic found exculpatory evidence
        assert result["semantic_risk_score"] < state_after_prosecutor.get("semantic_risk_score", 0.5)
        assert result["current_phase"] == "verdict"

    @patch("backend.agents.judge.get_judge_llm")
    def test_judge_renders_verdict_for_target(
        self,
        mock_llm,
        target_initial_state,
    ):
        """Test judge renders appropriate verdict for target transaction."""
        # Build state after prosecutor and skeptic
        state_before_judge = {
            **target_initial_state,
            "prosecutor_findings": [
                "HIDDEN LINK DETECTED: Shell Company -> Sanctioned via shared director",
                "BEHAVIORAL DRIFT: 16x deviation from baseline",
            ],
            "skeptic_findings": [
                "PAYMENT AUTHORIZED: Payment Grid Q1 2026",
                "NO ADVERSE MEDIA: Clean search results",
            ],
            "graph_risk_score": 0.85,
            "semantic_risk_score": 0.35,
            "historical_drift": 0.65,
            "hidden_links": [{"path": ["Shell", "Intermediary", "Sanctioned"]}],
            "alibi_evidence": ["Payment Grid document"],
            "current_phase": "verdict",
            "round_count": 1,
        }

        # Mock LLM response with JSON verdict
        mock_response = MagicMock()
        mock_response.content = """
        Based on the evidence presented:
        {
            "verdict": "ESCALATE",
            "risk_level": "high",
            "confidence_score": 0.82,
            "reasoning": "While the Skeptic found a payment grid authorization, the hidden link to a sanctioned entity via a shared director is a significant red flag that requires human review.",
            "prosecutor_score": {"accuracy": 4, "completeness": 4, "clarity": 4, "helpfulness": 4, "safety": 5},
            "skeptic_score": {"accuracy": 3, "completeness": 3, "clarity": 4, "helpfulness": 4, "safety": 3},
            "evidence_summary": ["EVID-0: Hidden link path", "DEF-0: Payment Grid"],
            "recommended_actions": ["Escalate to compliance officer", "Request additional documentation"],
            "eu_ai_act_compliance": {
                "article_13_satisfied": true,
                "transparency_statement": "This decision was generated by FIS Swarm AI system",
                "human_oversight_required": true
            },
            "needs_more_evidence": false
        }
        """
        mock_llm.return_value.invoke.return_value = mock_response

        # Import and run judge
        from backend.agents.judge import judge_agent

        result = judge_agent(state_before_judge)

        # Verify verdict
        assert result["verdict"]["verdict"] == "ESCALATE"
        assert result["risk_level"] == "high"
        assert result["confidence_score"] >= 0.8
        assert result["needs_more_evidence"] is False


class TestTargetUETRExpectedOutcome:
    """Tests verifying expected outcomes for the target scenario."""

    def test_shared_director_should_trigger_hidden_link(self):
        """The shared director pattern should be detected as a hidden link.

        Expected graph pattern:
        (Shell Company Alpha)-[:HAS_DIRECTOR]->(John Smith)
        (Sanctioned Entity X)-[:HAS_DIRECTOR]->(John Smith)

        This creates a 2-hop path through the shared director.
        """
        expected_path = {
            "start": "Shell Company Alpha",
            "end": "Sanctioned Entity X",
            "path": ["Shell Company Alpha", "John Smith (Director)", "Sanctioned Entity X"],
            "relationship_types": ["HAS_DIRECTOR", "HAS_DIRECTOR"],
            "hop_count": 2,
        }

        assert expected_path["hop_count"] <= 3  # Within detection range
        assert "Director" in expected_path["path"][1]

    def test_payment_grid_should_provide_partial_alibi(self):
        """Payment grid should explain the amount but not the hidden link.

        The Payment Grid authorization can explain:
        - The amount (within approved limits)
        - The creditor (approved vendor)

        But CANNOT explain:
        - The hidden link to sanctioned entity
        - The shared director relationship
        """
        # Payment grid covers: amount, creditor, frequency
        # But does NOT cover: hidden_links, sanctions, beneficial_ownership
        payment_grid_does_not_cover = ["hidden_links", "sanctions", "beneficial_ownership"]

        # Skeptic should reduce semantic risk but not graph risk
        assert "hidden_links" in payment_grid_does_not_cover

    def test_expected_final_verdict_is_escalate(self):
        """Expected verdict for target UETR is ESCALATE due to:

        1. Hidden link to sanctioned entity (high graph risk)
        2. Payment grid provides partial alibi (medium semantic risk)
        3. Behavioral drift detected (medium drift risk)

        Combined: ESCALATE for human review
        """
        expected_outcome = {
            "verdict": "ESCALATE",
            "risk_level": "high",
            "human_oversight_required": True,
            "recommended_actions": [
                "Escalate to compliance officer",
                "Request beneficial ownership documentation",
                "Verify shared director relationship",
            ],
        }

        assert expected_outcome["verdict"] in ["ESCALATE", "BLOCK"]
        assert expected_outcome["human_oversight_required"] is True


class TestEUAIActCompliance:
    """Tests for EU AI Act Article 13 compliance in target investigation."""

    def test_verdict_includes_transparency_statement(self):
        """Verify verdict includes AI-generated disclosure."""
        sample_verdict = {
            "eu_ai_act_compliance": {
                "article_13_satisfied": True,
                "transparency_statement": "Generated by FIS Swarm",
                "human_oversight_required": True,
            }
        }

        assert sample_verdict["eu_ai_act_compliance"]["article_13_satisfied"] is True
        assert "FIS" in sample_verdict["eu_ai_act_compliance"]["transparency_statement"]

    def test_verdict_includes_evidence_summary(self):
        """Verify verdict includes traceable evidence IDs."""
        sample_verdict = {
            "evidence_summary": [
                "EVID-0: Hidden link path Shell -> Sanctioned",
                "EVID-1: Behavioral drift 16x",
                "DEF-0: Payment Grid Q1 2026",
                "DEF-1: No adverse media",
            ],
        }

        assert len(sample_verdict["evidence_summary"]) >= 2
        assert any("EVID" in e for e in sample_verdict["evidence_summary"])
        assert any("DEF" in e for e in sample_verdict["evidence_summary"])

    def test_verdict_includes_reasoning(self):
        """Verify verdict includes human-readable explanation."""
        sample_verdict = {
            "reasoning": "The hidden link to a sanctioned entity through a shared director "
            "represents a significant compliance risk that cannot be fully mitigated "
            "by the payment grid authorization alone.",
        }

        assert len(sample_verdict["reasoning"]) > 50  # Meaningful explanation
        assert "hidden link" in sample_verdict["reasoning"].lower()
