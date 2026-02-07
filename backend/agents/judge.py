"""Judge Agent - Impartial Adjudicator in AML Investigation.

This agent is responsible for weighing evidence from both the Prosecutor
and Skeptic, evaluating the quality of their arguments, and rendering
a fair verdict with appropriate risk assessment.

The Judge ensures EU AI Act compliance by providing transparent reasoning,
confidence levels, and clear recommendations for human oversight.
"""

import json
import re
import logging
from typing import Dict, Any, Literal
from datetime import datetime

from langchain_core.messages import SystemMessage, HumanMessage
from backend.models.state import AgentState, DebateMessage
from backend.llm_provider import get_llm, invoke_with_fallback

logger = logging.getLogger(__name__)

# Production-grade system prompt for impartial adjudication
JUDGE_SYSTEM_PROMPT = """You are the presiding Judge in a Financial Crimes Investigation Tribunal.

## YOUR ROLE
You are the JUDGE - an impartial adjudicator who evaluates arguments from both the Prosecutor (accusation) and Skeptic (defense) to render a fair, evidence-based verdict.

## JUDICIAL PRINCIPLES
1. **Presumption of Legitimacy**: Transactions are legitimate until proven suspicious with material evidence
2. **Burden of Proof**: The Prosecutor must demonstrate suspicious indicators; circumstantial evidence alone is insufficient
3. **Right to Defense**: The Skeptic's exculpatory evidence must be fairly weighed
4. **Proportionality**: Recommended actions must be proportionate to the risk level

## EVALUATION FRAMEWORK

### Agent Performance Scoring (1-5 each)
| Criterion | Description |
|-----------|-------------|
| **Accuracy** | Are claims factually supported by tool results and evidence? |
| **Completeness** | Were all relevant investigative avenues explored? |
| **Clarity** | Are arguments logically structured and easy to follow? |
| **Objectivity** | Does the agent acknowledge limitations and uncertainties? |
| **Relevance** | Is the evidence material to the investigation? |

### Risk Level Determination
| Level | Threshold | Action |
|-------|-----------|--------|
| **CRITICAL** | Combined risk ≥ 0.85 | Immediate block, file SAR, escalate to MLRO |
| **HIGH** | Combined risk ≥ 0.65 | Block pending human review, enhanced due diligence |
| **MEDIUM** | Combined risk ≥ 0.40 | Enhanced monitoring, request additional documentation |
| **LOW** | Combined risk < 0.40 | Approve with standard monitoring |

### Verdict Options
| Verdict | When to Use |
|---------|-------------|
| **APPROVE** | Low risk, exculpatory evidence outweighs concerns |
| **BLOCK** | High/Critical risk, material suspicious indicators, insufficient defense |
| **ESCALATE** | Complex case requiring senior compliance review |
| **REVIEW** | Insufficient evidence for conclusive determination |

## EU AI ACT COMPLIANCE (Mandatory)

Per Regulation (EU) 2024/1689 Article 13 (Transparency):
1. Provide clear explanation of decision rationale
2. List all evidence considered in reaching verdict
3. State confidence level with justification
4. Identify what additional evidence would change the verdict
5. Indicate whether human oversight is required

## OUTPUT REQUIREMENTS

You MUST output a valid JSON object with this exact structure:

```json
{
    "verdict": "APPROVE" | "BLOCK" | "ESCALATE" | "REVIEW",
    "risk_level": "low" | "medium" | "high" | "critical",
    "confidence_score": 0.0-1.0,
    "reasoning": "Detailed explanation of how you weighed the evidence and reached this verdict...",
    "prosecutor_score": {
        "accuracy": 1-5,
        "completeness": 1-5,
        "clarity": 1-5,
        "objectivity": 1-5,
        "relevance": 1-5,
        "total": 5-25
    },
    "skeptic_score": {
        "accuracy": 1-5,
        "completeness": 1-5,
        "clarity": 1-5,
        "objectivity": 1-5,
        "relevance": 1-5,
        "total": 5-25
    },
    "evidence_summary": [
        "EVID-001: Hidden link to sanctioned entity detected",
        "DEF-001: Legitimate business relationship documented"
    ],
    "key_factors": [
        "Primary factor in decision",
        "Secondary factor in decision"
    ],
    "recommended_actions": [
        "Specific action 1",
        "Specific action 2"
    ],
    "eu_ai_act_compliance": {
        "article_13_satisfied": true,
        "transparency_statement": "This verdict was reached by weighing X evidence items from Prosecutor against Y items from Skeptic...",
        "human_oversight_required": true,
        "additional_context_needed": ["What additional evidence would help"]
    },
    "needs_more_evidence": false,
    "additional_questions": []
}
```

## SPECIAL INSTRUCTIONS

1. If confidence < 0.80 AND round < 3: Set needs_more_evidence = true and list specific questions
2. If hidden links to sanctioned entities exist with no valid business explanation: Recommend BLOCK
3. If exculpatory evidence fully explains suspicious patterns: Recommend APPROVE
4. When in doubt: Recommend ESCALATE (human judgment needed)

Be fair, be thorough, be transparent.
"""


def get_judge_llm():
    """Get the LLM for the Judge agent.

    Uses very low temperature for consistent, reproducible verdicts
    that prioritize accuracy over creativity.
    """
    return get_llm(temperature=0.1)


def calculate_risk_level(
    graph_risk: float, semantic_risk: float, drift: float
) -> Literal["low", "medium", "high", "critical"]:
    """Calculate overall risk level from component scores.

    Uses weighted combination:
    - Graph risk (hidden links, fraud rings): 50%
    - Semantic risk (document analysis): 30%
    - Behavioral drift: 20%

    Args:
        graph_risk: Risk score from graph analysis (0.0-1.0)
        semantic_risk: Risk score from document analysis (0.0-1.0)
        drift: Behavioral drift score (0.0-1.0)

    Returns:
        Risk level category
    """
    combined_risk = (graph_risk * 0.5) + (semantic_risk * 0.3) + (drift * 0.2)

    if combined_risk >= 0.85:
        return "critical"
    elif combined_risk >= 0.65:
        return "high"
    elif combined_risk >= 0.40:
        return "medium"
    else:
        return "low"


def _extract_json_from_response(response_content: str) -> Dict[str, Any]:
    """Extract JSON object from LLM response with multiple fallback strategies.

    Args:
        response_content: Raw response string from LLM

    Returns:
        Parsed JSON dictionary

    Raises:
        ValueError: If no valid JSON can be extracted
    """
    # Strategy 1: Look for JSON code block
    json_match = re.search(
        r"```(?:json)?\s*(\{.*?\})\s*```", response_content, re.DOTALL
    )

    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass

    # Strategy 2: Find outermost curly braces
    json_start = response_content.find("{")
    json_end = response_content.rfind("}") + 1

    if json_start != -1 and json_end > json_start:
        try:
            json_str = response_content[json_start:json_end]
            return json.loads(json_str)
        except json.JSONDecodeError:
            pass

    # Strategy 3: Try the whole string
    try:
        return json.loads(response_content)
    except json.JSONDecodeError:
        pass

    raise ValueError("Could not extract valid JSON from response")


def _extract_fields_via_regex(
    response_content: str,
    graph_risk: float,
    semantic_risk: float,
    historical_drift: float,
) -> Dict[str, Any]:
    """Extract verdict fields using regex as fallback.

    Args:
        response_content: Raw response string
        graph_risk: Graph risk score for calculating default risk level
        semantic_risk: Semantic risk score
        historical_drift: Drift score

    Returns:
        Dictionary with extracted/default fields
    """
    verdict_match = re.search(r'"verdict":\s*"([^"]+)"', response_content)
    risk_match = re.search(r'"risk_level":\s*"([^"]+)"', response_content)
    confidence_match = re.search(r'"confidence_score":\s*([\d.]+)', response_content)
    reasoning_match = re.search(
        r'"reasoning":\s*"([^"]*(?:[^"\\]|\\.)*)"', response_content
    )

    detected_verdict = verdict_match.group(1) if verdict_match else "REVIEW"
    detected_risk = (
        risk_match.group(1)
        if risk_match
        else calculate_risk_level(graph_risk, semantic_risk, historical_drift)
    )
    detected_confidence = float(confidence_match.group(1)) if confidence_match else 0.5

    if reasoning_match:
        clean_reasoning = reasoning_match.group(1)
    else:
        # Extract readable text, removing JSON artifacts
        clean_reasoning = (
            response_content.replace("{", "")
            .replace("}", "")
            .replace("```json", "")
            .replace("```", "")
            .replace('"', "")
            .strip()[:500]
        )
        if len(clean_reasoning) > 490:
            clean_reasoning += "..."

    return {
        "verdict": detected_verdict,
        "risk_level": detected_risk,
        "confidence_score": detected_confidence,
        "reasoning": clean_reasoning,
        "needs_more_evidence": True,
        "eu_ai_act_compliance": {
            "article_13_satisfied": True,
            "transparency_statement": "Verdict extracted via fallback parsing due to response format issues.",
            "human_oversight_required": True,
        },
        "recommended_actions": ["Review case manually due to parsing uncertainty"],
    }


def judge_agent(state: AgentState) -> Dict[str, Any]:
    """The Judge agent - weighs evidence and renders verdict.

    This agent evaluates the cases presented by both the Prosecutor
    and Skeptic, scores their performance, and renders an impartial
    verdict with appropriate risk assessment and recommendations.

    Args:
        state: Current investigation state containing all evidence,
               agent findings, and debate history

    Returns:
        State update dictionary containing:
        - verdict: Structured verdict dictionary
        - risk_level: Determined risk level
        - confidence_score: Judge's confidence in verdict
        - messages: Updated message list with judge's verdict
        - needs_more_evidence: Whether another round is needed
        - round_count: Incremented round counter
        - current_phase: Next phase indicator
    """
    logger.info(f"Judge agent evaluating case for UETR: {state.get('uetr', 'Unknown')}")

    llm = get_judge_llm()

    # Extract transaction context
    iso_message = state.get("iso_message", {})
    debtor_name = iso_message.get("debtor", {}).get("name", "Unknown Debtor")
    creditor_name = iso_message.get("creditor", {}).get("name", "Unknown Creditor")
    amount = iso_message.get("amount", {})
    uetr = state.get("uetr", "")

    # Get agent findings
    prosecutor_findings = state.get("prosecutor_findings", [])
    skeptic_findings = state.get("skeptic_findings", [])

    # Get risk scores
    graph_risk = state.get("graph_risk_score", 0.0)
    semantic_risk = state.get("semantic_risk_score", 0.5)
    historical_drift = state.get("historical_drift", 0.0)

    # Get evidence
    hidden_links = state.get("hidden_links", [])
    alibi_evidence = state.get("alibi_evidence", [])

    round_count = state.get("round_count", 1)

    # Calculate preliminary risk for context
    calculated_risk = calculate_risk_level(graph_risk, semantic_risk, historical_drift)
    combined_risk_score = (
        (graph_risk * 0.5) + (semantic_risk * 0.3) + (historical_drift * 0.2)
    )

    # Format prosecution case
    prosecution_case = "### Prosecutor's Case\n"
    if prosecutor_findings:
        for i, finding in enumerate(prosecutor_findings[:10]):
            prosecution_case += f"**EVID-{i + 1:03d}**: {finding}\n\n"
    else:
        prosecution_case += "*No specific findings submitted by Prosecutor*\n"

    # Format defense case
    defense_case = "### Skeptic's Defense\n"
    if skeptic_findings:
        for i, finding in enumerate(skeptic_findings[:10]):
            defense_case += f"**DEF-{i + 1:03d}**: {finding}\n\n"
    else:
        defense_case += "*No specific defense submitted by Skeptic*\n"

    # Format debate history
    message_history = state.get("messages", [])
    history_text = ""
    if message_history:
        history_text = "\n## DEBATE TRANSCRIPT\n"
        for msg in message_history[-8:]:  # Last 8 messages
            speaker = msg.get("speaker", "unknown").upper()
            content = msg.get("content", "")
            if len(content) > 500:
                content = content[:500] + "... [truncated for brevity]"
            history_text += f"**{speaker}**: {content}\n\n---\n\n"

    # Construct judgment prompt
    judgment_prompt = f"""## CASE FILE: {uetr}

### Transaction Summary
| Field | Value |
|-------|-------|
| UETR | `{uetr}` |
| Debtor (Originator) | {debtor_name} |
| Creditor (Beneficiary) | {creditor_name} |
| Amount | {amount.get("value", "0")} {amount.get("currency", "EUR")} |
| Purpose | {iso_message.get("purpose_code", "N/A")} |

### Quantitative Risk Assessment
| Risk Type | Score | Weight | Contribution |
|-----------|-------|--------|--------------|
| Graph Risk (hidden links, fraud rings) | {graph_risk:.2f} | 50% | {graph_risk * 0.5:.2f} |
| Semantic Risk (document analysis) | {semantic_risk:.2f} | 30% | {semantic_risk * 0.3:.2f} |
| Behavioral Drift | {historical_drift:.2f} | 20% | {historical_drift * 0.2:.2f} |
| **Combined Risk Score** | | | **{combined_risk_score:.2f}** |
| **Calculated Risk Level** | | | **{calculated_risk.upper()}** |

---

{prosecution_case}

**Hidden Links to High-Risk Entities**: {len(hidden_links)}
{json.dumps(hidden_links[:3], indent=2, default=str) if hidden_links else "None detected"}

---

{defense_case}

**Exculpatory Documents Found**: {len(alibi_evidence)}
{chr(10).join(f"- {e[:100]}..." if len(str(e)) > 100 else f"- {e}" for e in alibi_evidence[:3]) if alibi_evidence else "None submitted"}

---

## JUDICIAL PARAMETERS

- **Debate Round**: {round_count} of 3
- **Minimum Confidence for Final Verdict**: 0.80
- **Current Status**: {"Final round - must render verdict" if round_count >= 3 else "May request additional evidence if confidence < 0.80"}

{history_text}

---

## YOUR TASK

1. Score both agents (Prosecutor and Skeptic) using the 5 criteria
2. Weigh the incriminating evidence against the exculpatory evidence
3. Determine if the suspicious patterns are adequately explained
4. Render your verdict with full reasoning
5. Ensure EU AI Act Article 13 transparency compliance

Output your verdict as a properly formatted JSON object.
"""

    messages = [
        SystemMessage(content=JUDGE_SYSTEM_PROMPT),
        HumanMessage(content=judgment_prompt),
    ]

    # Invoke LLM
    try:
        response = invoke_with_fallback(llm, messages)
    except Exception as e:
        logger.error(f"Judge LLM invocation failed: {e}")
        # Return conservative fallback verdict
        fallback_verdict = {
            "verdict": "ESCALATE",
            "risk_level": calculated_risk,
            "confidence_score": 0.3,
            "reasoning": f"Unable to complete judicial evaluation due to system error: {str(e)}. Escalating for human review.",
            "needs_more_evidence": False,
            "eu_ai_act_compliance": {
                "article_13_satisfied": False,
                "transparency_statement": "System error prevented full evaluation.",
                "human_oversight_required": True,
            },
            "recommended_actions": ["Escalate to senior compliance for manual review"],
        }

        debate_message: DebateMessage = {
            "speaker": "judge",
            "content": f"**Verdict: ESCALATE** (System Error)\n\n{fallback_verdict['reasoning']}",
            "evidence_ids": [],
            "timestamp": datetime.now().isoformat(),
        }

        return {
            "verdict": fallback_verdict,
            "risk_level": calculated_risk,
            "confidence_score": 0.3,
            "messages": [debate_message],
            "needs_more_evidence": False,
            "round_count": round_count + 1,
            "current_phase": "verdict",
        }

    # Extract response content
    raw_content = response.content if hasattr(response, "content") else str(response)
    if isinstance(raw_content, list):
        response_content = "\n".join(str(item) for item in raw_content)
    else:
        response_content = str(raw_content)

    # Parse JSON verdict
    try:
        verdict_json = _extract_json_from_response(response_content)

        if not isinstance(verdict_json, dict):
            raise ValueError("Parsed JSON is not a dictionary")

    except (ValueError, json.JSONDecodeError) as e:
        logger.warning(f"JSON parsing failed, using regex fallback: {e}")
        verdict_json = _extract_fields_via_regex(
            response_content, graph_risk, semantic_risk, historical_drift
        )

    # Extract key fields with defaults
    confidence = float(verdict_json.get("confidence_score", 0.5))
    needs_more = verdict_json.get("needs_more_evidence", False)

    # Determine if more evidence is needed
    if confidence < 0.8 and round_count < 3:
        needs_more = True
        logger.info(
            f"Low confidence ({confidence:.2f}) in round {round_count}, requesting more evidence"
        )

    # Finalize risk level
    risk_level = verdict_json.get("risk_level", calculated_risk)

    # Build human-readable verdict message
    verdict_decision = verdict_json.get("verdict", "REVIEW")
    reasoning = verdict_json.get("reasoning", "No reasoning provided")
    confidence_pct = int(confidence * 100)

    # Format debate content for display
    debate_content = f"""## Judicial Verdict: {verdict_decision}

**Risk Level**: {risk_level.upper()} | **Confidence**: {confidence_pct}%

### Reasoning
{reasoning}
"""

    # Add key factors if present
    key_factors = verdict_json.get("key_factors", [])
    if key_factors:
        debate_content += "\n### Key Factors in Decision\n"
        for factor in key_factors[:5]:
            debate_content += f"- {factor}\n"

    # Add recommended actions
    recommended_actions = verdict_json.get("recommended_actions", [])
    if recommended_actions:
        debate_content += "\n### Recommended Actions\n"
        for action in recommended_actions[:5]:
            debate_content += f"- {action}\n"

    # Add transparency statement
    eu_compliance = verdict_json.get("eu_ai_act_compliance", {})
    if eu_compliance.get("transparency_statement"):
        debate_content += (
            f"\n### EU AI Act Transparency\n{eu_compliance['transparency_statement']}\n"
        )

    # Note if more evidence needed
    if needs_more:
        additional_questions = verdict_json.get("additional_questions", [])
        debate_content += "\n### Additional Evidence Required\n"
        if additional_questions:
            for q in additional_questions[:3]:
                debate_content += f"- {q}\n"
        else:
            debate_content += (
                "- Further investigation needed before final determination\n"
            )

    # Create debate message
    evidence_summary = verdict_json.get("evidence_summary", [])
    debate_message: DebateMessage = {
        "speaker": "judge",
        "content": debate_content,
        "evidence_ids": evidence_summary[:15] if evidence_summary else [],
        "timestamp": datetime.now().isoformat(),
    }

    logger.info(
        f"Judge verdict rendered: {verdict_decision}, "
        f"Risk: {risk_level}, Confidence: {confidence:.2f}, "
        f"Needs more evidence: {needs_more}"
    )

    return {
        "verdict": verdict_json,
        "risk_level": risk_level,
        "confidence_score": confidence,
        "messages": [debate_message],
        "needs_more_evidence": needs_more,
        "round_count": round_count + 1,
        "current_phase": "investigation" if needs_more else "complete",
    }
