"""Skeptic Agent - Defense Advocate in AML Investigation.

This agent is responsible for finding exculpatory evidence that explains
suspicious patterns. It searches for legitimate business justifications,
regulatory compliance context, and normal behavioral patterns.

The Skeptic provides balance to the Prosecutor's accusations, ensuring
fair assessment before the Judge renders a verdict.
"""

import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from langchain_core.messages import SystemMessage, HumanMessage
from backend.models.state import AgentState, DebateMessage
from backend.tools.tools_docs import (
    search_alibi,
    consult_regulation,
    search_payment_justification,
    search_adverse_media,
)
from backend.tools.tools_memory import get_entity_profile, compare_to_peer_group
from backend.llm_provider import get_llm, invoke_with_fallback

logger = logging.getLogger(__name__)

# Production-grade system prompt for the defense advocate
SKEPTIC_SYSTEM_PROMPT = """You are an expert Financial Defense Analyst specializing in compliance investigations.

## YOUR ROLE
You are the SKEPTIC (Defense Advocate) in a multi-agent compliance system. Your mission is to find EXCULPATORY evidence that provides legitimate explanations for patterns the Prosecutor has flagged as suspicious.

## CORE PRINCIPLE
Many transactions flagged as "suspicious" have perfectly legitimate business explanations. Your job is to find these explanations through rigorous research, NOT to defend clearly criminal activity.

## AVAILABLE DEFENSE TOOLS
Use these tools to build your defense case:

1. **search_alibi** - Search internal documents for legitimate business explanations (contracts, agreements, correspondence)
2. **consult_regulation** - Research regulatory guidance that may support the transaction's legitimacy
3. **search_payment_justification** - Find authorized payment grids, standing orders, recurring payment schedules
4. **search_adverse_media** - Verify absence of negative media coverage (important for clearing entities)
5. **get_entity_profile** - Retrieve entity profile showing normal operational patterns
6. **compare_to_peer_group** - Compare behavior to industry peers to show normalcy

## DEFENSE PROTOCOL
For EACH of the Prosecutor's findings, you must:

1. **Understand the Allegation**: What exactly is the Prosecutor claiming?
2. **Search for Justification**: Use appropriate tools to find exculpatory evidence
3. **Evaluate the Evidence**: Does this evidence actually explain the suspicious pattern?
4. **Document the Defense**: Cite specific documents, regulations, or data points

## EVIDENCE CATEGORIES TO SEARCH

### For "Hidden Links" allegations:
- Legitimate business relationships (supplier, customer, partner)
- Common corporate ownership structures (not indicative of concealment)
- Industry standard trading relationships

### For "Structuring" allegations:
- Regular payment schedules (payroll, rent, subscriptions)
- Authorized payment grids matching the amounts
- Business operational patterns

### For "Behavioral Drift" allegations:
- Seasonal business variations
- Business expansion or contraction
- Industry-wide trends affecting all players

### For "Prior Investigation History":
- Resolution outcomes (cleared, false positive)
- Remediation actions taken
- Time elapsed since prior issues

## OUTPUT REQUIREMENTS
Structure your defense brief as follows:

### DEFENSE SUMMARY
[2-3 sentence summary of your defense position]

### POINT-BY-POINT REBUTTAL
For each Prosecutor finding:
- **Defense ID**: DEF-001, DEF-002, etc.
- **Prosecutor's Claim**: [summarize the allegation]
- **Exculpatory Evidence**: [what you found]
- **Source**: [document/regulation/data reference]
- **Assessment**: FULLY EXPLAINED / PARTIALLY EXPLAINED / UNEXPLAINED

### EXCULPATORY EVIDENCE INVENTORY
List all supporting evidence found with references

### RESIDUAL CONCERNS
- Any allegations you CANNOT explain (intellectual honesty is critical)
- Uncertainty factors that remain

### RECOMMENDED CONSIDERATION
Based on your defense findings, advise the Judge whether:
- Full exoneration is warranted (APPROVE)
- Reduced risk assessment appropriate (REVIEW)
- Concerns remain despite defense (no change to risk)

## PROFESSIONAL STANDARDS
- Be thorough but honest - do not overstate your defense
- If evidence is weak, acknowledge it
- Cite specific documents and regulations
- Distinguish between "explained" and "possibly explained"
- Your credibility depends on intellectual honesty
"""


def get_skeptic_llm():
    """Get the LLM for the Skeptic agent.

    Uses moderate temperature for balanced analysis that is
    thorough in finding exculpatory evidence but not creative
    in manufacturing defenses.
    """
    return get_llm(temperature=0.3)


def _execute_tool(
    tool_name: str, tool_args: Dict[str, Any], debtor_name: str
) -> Optional[Dict[str, Any]]:
    """Execute a tool and return the result with error handling.

    Args:
        tool_name: Name of the tool to execute
        tool_args: Arguments for the tool
        debtor_name: Default entity name to use if not specified

    Returns:
        Tool result dictionary or None if tool not found
    """
    try:
        if tool_name == "search_alibi":
            query = tool_args.get("query", f"legitimate business {debtor_name}")
            entity = tool_args.get("entity_name", debtor_name)
            return search_alibi.invoke({"query": query, "entity_name": entity})

        elif tool_name == "search_payment_justification":
            entity = tool_args.get("entity_name", debtor_name)
            return search_payment_justification.invoke({"entity_name": entity})

        elif tool_name == "consult_regulation":
            query = tool_args.get("query", "transparency requirements high risk AI")
            reg_type = tool_args.get("regulation_type", "eu_ai_act")
            return consult_regulation.invoke(
                {"query": query, "regulation_type": reg_type}
            )

        elif tool_name == "get_entity_profile":
            entity = tool_args.get("entity_id", debtor_name)
            return get_entity_profile.invoke({"entity_id": entity})

        elif tool_name == "compare_to_peer_group":
            entity = tool_args.get("entity_id", debtor_name)
            return compare_to_peer_group.invoke({"entity_id": entity})

        elif tool_name == "search_adverse_media":
            entity = tool_args.get("entity_name", debtor_name)
            return search_adverse_media.invoke({"entity_name": entity})

        else:
            logger.warning(f"Unknown tool requested: {tool_name}")
            return None

    except Exception as e:
        logger.error(f"Tool execution failed for {tool_name}: {e}")
        return {"error": str(e), "tool": tool_name}


def _process_tool_results(
    tool_name: str,
    tool_result: Dict[str, Any],
    findings: List[str],
    alibi_evidence: List[str],
    risk_reduction: float,
) -> float:
    """Process tool results and update findings and risk reduction.

    Args:
        tool_name: Name of the executed tool
        tool_result: Result from the tool
        findings: List to append findings to (modified in place)
        alibi_evidence: List to append alibi evidence (modified in place)
        risk_reduction: Current risk reduction score

    Returns:
        Updated risk reduction score
    """
    if not tool_result or "error" in tool_result:
        return risk_reduction

    if tool_name == "search_alibi":
        if tool_result.get("has_alibi"):
            evidence_items = tool_result.get("evidence", [])
            for e in evidence_items:
                if isinstance(e, dict) and "content" in e:
                    alibi_evidence.append(e["content"])
            risk_reduction += 0.2
            findings.append(
                f"LEGITIMATE BUSINESS CONTEXT FOUND: {len(evidence_items)} supporting document(s) "
                f"provide business justification for the transaction pattern."
            )

    elif tool_name == "search_payment_justification":
        if tool_result.get("has_valid_authorization"):
            justifications = tool_result.get("justifications", [])
            for j in justifications:
                if isinstance(j, dict) and "content" in j:
                    alibi_evidence.append(j["content"])
            risk_reduction += 0.3
            payment_type = tool_result.get("payment_type", "authorized payment")
            findings.append(
                f"AUTHORIZED PAYMENT FOUND: Transaction matches {payment_type} schedule. "
                f"Amount is consistent with established payment grid."
            )

    elif tool_name == "consult_regulation":
        reg_guidance = tool_result.get("guidance", "")
        if reg_guidance:
            findings.append(
                f"REGULATORY CONTEXT: {reg_guidance[:200]}..."
                if len(str(reg_guidance)) > 200
                else f"REGULATORY CONTEXT: {reg_guidance}"
            )

    elif tool_name == "get_entity_profile":
        if tool_result.get("profile_completeness") == "complete":
            risk_reduction += 0.1
            risk_flags = tool_result.get("risk_flags", [])
            if not risk_flags:
                findings.append(
                    "CLEAN ENTITY PROFILE: Entity has complete profile with no outstanding risk flags. "
                    "Historical behavior pattern is consistent and well-documented."
                )
            else:
                findings.append(
                    f"ENTITY PROFILE: Profile is complete. Some flags exist: {', '.join(risk_flags[:3])}"
                )

    elif tool_name == "compare_to_peer_group":
        if tool_result.get("within_peer_norms"):
            risk_reduction += 0.15
            percentile = tool_result.get("percentile", "N/A")
            findings.append(
                f"INDUSTRY NORMAL BEHAVIOR: Entity's transaction patterns are within peer group norms. "
                f"Percentile ranking: {percentile}. No outlier behavior detected."
            )
        else:
            deviation = tool_result.get("deviation_factor", "unknown")
            findings.append(
                f"PEER COMPARISON NOTE: Entity shows some deviation from peer norms "
                f"(deviation factor: {deviation}), but this alone is not indicative of wrongdoing."
            )

    elif tool_name == "search_adverse_media":
        media_risk = tool_result.get("adverse_media_risk", "unknown")
        if media_risk == "low":
            risk_reduction += 0.1
            findings.append(
                "NO ADVERSE MEDIA: Media scan found no negative coverage. "
                "Entity has clean public reputation."
            )
        elif media_risk == "high":
            # This is incriminating, not exculpatory - note it honestly
            media_details = tool_result.get("details", "unspecified concerns")
            findings.append(
                f"ADVERSE MEDIA FOUND (NOTE: Incriminating, not exculpatory): {media_details}"
            )
            # Increase risk slightly since this is negative for defense
            risk_reduction -= 0.1

    return risk_reduction


def skeptic_agent(state: AgentState) -> Dict[str, Any]:
    """The Skeptic agent - seeks exculpatory evidence.

    This agent is responsible for finding legitimate explanations for
    patterns flagged as suspicious by the Prosecutor. It searches
    documents, regulations, and behavioral data to build a defense case.

    Args:
        state: Current investigation state containing transaction details,
               prosecutor findings, and debate history

    Returns:
        State update dictionary containing:
        - skeptic_findings: List of defense findings
        - messages: Debate message from skeptic
        - tool_calls: Record of all tool invocations
        - doc_context: Accumulated document search results
        - alibi_evidence: Exculpatory evidence found
        - semantic_risk_score: Adjusted risk score after defense
        - current_phase: Next phase indicator
    """
    logger.info(
        f"Skeptic agent starting defense for UETR: {state.get('uetr', 'Unknown')}"
    )

    llm = get_skeptic_llm()
    tools = [
        search_alibi,
        consult_regulation,
        search_payment_justification,
        search_adverse_media,
        get_entity_profile,
        compare_to_peer_group,
    ]

    # Extract context
    iso_message = state.get("iso_message", {})
    debtor_name = iso_message.get("debtor", {}).get("name", "Unknown Debtor")
    creditor_name = iso_message.get("creditor", {}).get("name", "Unknown Creditor")
    amount = iso_message.get("amount", {})
    uetr = state.get("uetr", "")

    # Get prosecutor's accusations
    prosecutor_findings = state.get("prosecutor_findings", [])
    graph_context = state.get("graph_context", "")

    # Format prosecution case for rebuttal
    prosecution_case = ""
    if prosecutor_findings:
        prosecution_case = "## PROSECUTOR'S ALLEGATIONS TO REBUT\n\n"
        for i, finding in enumerate(prosecutor_findings):
            prosecution_case += f"**Allegation {i + 1}**: {finding}\n\n"
    else:
        prosecution_case = "## PROSECUTOR'S ALLEGATIONS\nNo specific allegations provided by Prosecutor.\n"

    # Build debate history context
    message_history = state.get("messages", [])
    history_text = ""
    if message_history:
        history_text = "\n## DEBATE HISTORY\n"
        for msg in message_history[-4:]:
            speaker = msg.get("speaker", "unknown").upper()
            content = msg.get("content", "")
            if len(content) > 400:
                content = content[:400] + "... [truncated]"
            history_text += f"**{speaker}**: {content}\n\n"

    # Construct defense prompt
    defense_prompt = f"""## TRANSACTION UNDER INVESTIGATION

| Field | Value |
|-------|-------|
| UETR | `{uetr}` |
| Debtor (Originator) | {debtor_name} |
| Creditor (Beneficiary) | {creditor_name} |
| Amount | {amount.get("value", "0")} {amount.get("currency", "EUR")} |

**Defense Round**: {state.get("round_count", 1)} of 3

{prosecution_case}

## GRAPH ANALYSIS CONTEXT
{graph_context[:1000] if graph_context else "No graph analysis context available."}

{history_text}

## YOUR DEFENSE MISSION

For each of the Prosecutor's allegations, you must:

1. **Search for payment justifications** for {debtor_name} - check for authorized payment schedules
2. **Search for alibi evidence** - legitimate business explanations
3. **Verify entity profile** shows normal operational patterns
4. **Compare to peer group** to demonstrate industry-normal behavior
5. **Check adverse media** to verify clean public record
6. **Consult regulations** for compliance context

Build the strongest possible evidence-based defense. Be thorough but intellectually honest.
If you cannot explain an allegation, say so clearly.
"""

    messages = [
        SystemMessage(content=SKEPTIC_SYSTEM_PROMPT),
        HumanMessage(content=defense_prompt),
    ]

    # Initialize tracking variables
    findings: List[str] = []
    doc_context = ""
    alibi_evidence: List[str] = []
    risk_reduction = 0.0
    executed_tool_calls: List[Dict] = []

    # Invoke LLM with tools
    try:
        response = invoke_with_fallback(llm, messages, tools)
    except Exception as e:
        logger.error(f"LLM invocation failed: {e}")
        return {
            "skeptic_findings": [f"Defense analysis error: {str(e)}"],
            "messages": [
                {
                    "speaker": "skeptic",
                    "content": f"Defense analysis encountered an error: {str(e)}. Unable to complete review.",
                    "evidence_ids": [],
                    "timestamp": datetime.now().isoformat(),
                }
            ],
            "tool_calls": [],
            "current_phase": "verdict",
        }

    # Process tool calls
    if hasattr(response, "tool_calls") and response.tool_calls:
        for tool_call in response.tool_calls:
            tool_name = tool_call.get("name", "")
            tool_args = tool_call.get("args", {})

            logger.debug(f"Executing defense tool: {tool_name} with args: {tool_args}")

            # Execute the tool
            tool_result = _execute_tool(tool_name, tool_args, debtor_name)

            if tool_result:
                # Process results and update risk reduction
                risk_reduction = _process_tool_results(
                    tool_name, tool_result, findings, alibi_evidence, risk_reduction
                )

                # Accumulate document context
                doc_context += f"\n### {tool_name}\n{json.dumps(tool_result, default=str, indent=2)}\n"

            # Record tool call for audit trail
            executed_tool_calls.append(
                {
                    "agent": "skeptic",
                    "tool_name": tool_name,
                    "tool_args": tool_args,
                    "result": json.dumps(tool_result, default=str)
                    if tool_result
                    else "null",
                    "timestamp": datetime.now().isoformat(),
                }
            )

    # Extract final content from LLM response
    raw_content = response.content if hasattr(response, "content") else str(response)
    if isinstance(raw_content, list):
        final_content = "\n".join(str(item) for item in raw_content)
    else:
        final_content = str(raw_content)

    # Generate defense evidence IDs
    defense_ids = [f"DEF-{i + 1:03d}" for i in range(len(findings))]

    # Create formal debate message
    debate_message: DebateMessage = {
        "speaker": "skeptic",
        "content": final_content,
        "evidence_ids": defense_ids,
        "timestamp": datetime.now().isoformat(),
    }

    # Calculate adjusted semantic risk score
    current_semantic_risk = state.get("semantic_risk_score", 0.5)
    adjusted_risk = max(0.0, min(1.0, current_semantic_risk - risk_reduction))

    logger.info(
        f"Skeptic defense complete. Findings: {len(findings)}, "
        f"Risk reduction: {risk_reduction:.2f}, Adjusted risk: {adjusted_risk:.2f}"
    )

    return {
        "skeptic_findings": findings,
        "messages": [debate_message],
        "tool_calls": executed_tool_calls,
        "doc_context": doc_context,
        "alibi_evidence": alibi_evidence,
        "semantic_risk_score": adjusted_risk,
        "current_phase": "verdict",
    }
