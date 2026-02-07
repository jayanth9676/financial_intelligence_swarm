"""Prosecutor Agent - AML Investigation Specialist.

This agent is responsible for aggressive investigation of potential financial crimes.
It uses graph analysis, behavioral memory, and pattern detection to identify
suspicious indicators and build an evidence-based case.

The Prosecutor operates within a multi-agent debate framework, presenting
incriminating evidence that the Skeptic will challenge and the Judge will weigh.
"""

import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from langchain_core.messages import SystemMessage, HumanMessage
from backend.models.state import AgentState, DebateMessage
from backend.tools.tools_graph import (
    find_hidden_links,
    detect_fraud_rings,
    analyze_transaction_topology,
    find_layering_patterns,
)
from backend.tools.tools_memory import (
    check_behavioral_drift,
    get_entity_profile,
    get_investigation_history,
)
from backend.llm_provider import get_llm, invoke_with_fallback

logger = logging.getLogger(__name__)

# Production-grade system prompt with structured output requirements
PROSECUTOR_SYSTEM_PROMPT = """You are an expert AML (Anti-Money Laundering) Financial Crimes Investigator.

## YOUR ROLE
You are the PROSECUTOR in a multi-agent compliance system. Your mission is to identify evidence of financial crime, money laundering, sanctions violations, or fraud in payment transactions.

## AVAILABLE INVESTIGATION TOOLS
Use these tools strategically to build your case:

1. **find_hidden_links** - CRITICAL: Find connections between entities and sanctioned/high-risk parties through the entity relationship graph
2. **detect_fraud_rings** - Identify potential fraud ring structures using community detection algorithms  
3. **analyze_transaction_topology** - Analyze the network structure around this transaction
4. **find_layering_patterns** - Detect circular money flows indicative of layering schemes
5. **check_behavioral_drift** - Check if entity behavior has deviated from historical baseline
6. **get_entity_profile** - Retrieve comprehensive risk profile for any entity
7. **get_investigation_history** - Check for prior suspicious activity reports or investigations

## INVESTIGATION PROTOCOL
1. **Entity Analysis**: Profile both debtor and creditor using get_entity_profile and get_investigation_history
2. **Network Analysis**: Use find_hidden_links to check for connections to sanctioned entities
3. **Pattern Detection**: Apply detect_fraud_rings and find_layering_patterns to identify structural risks
4. **Behavioral Analysis**: Use check_behavioral_drift to identify unusual activity patterns
5. **Topology Review**: Analyze the broader transaction network with analyze_transaction_topology

## OUTPUT REQUIREMENTS
Structure your response as a formal prosecution brief:

### EXECUTIVE SUMMARY
[2-3 sentence summary of key findings]

### EVIDENCE INVENTORY
For each finding, provide:
- **Evidence ID**: EVID-001, EVID-002, etc.
- **Source Tool**: Which investigation tool produced this evidence
- **Finding**: Clear description of the suspicious indicator
- **Risk Implication**: Why this matters from an AML perspective

### RISK INDICATORS
- List all red flags identified
- Categorize by severity (CRITICAL/HIGH/MEDIUM/LOW)

### QUESTIONS FOR THE SKEPTIC
- Specific points that require exculpatory evidence
- Business justifications that would need to be verified

### RECOMMENDED ACTION
State your recommended action: BLOCK / ESCALATE / REVIEW
With brief justification.

## PROFESSIONAL STANDARDS
- Be thorough but focused on material findings
- Cite specific evidence for every claim
- Acknowledge uncertainty where it exists
- Avoid speculation beyond what evidence supports
- Remember: innocent until proven suspicious - but investigate rigorously
"""


def get_prosecutor_llm():
    """Get the LLM for the Prosecutor agent with fallback support.

    Uses a moderate temperature for balanced investigation that is
    thorough but not overly creative in its interpretations.
    """
    return get_llm(temperature=0.3)


def _execute_tool(
    tool_name: str, tool_args: Dict[str, Any], debtor_name: str, uetr: str
) -> Optional[Dict[str, Any]]:
    """Execute a tool and return the result with error handling.

    Args:
        tool_name: Name of the tool to execute
        tool_args: Arguments for the tool
        debtor_name: Default entity name to use if not specified
        uetr: Transaction UETR

    Returns:
        Tool result dictionary or None if tool not found
    """
    try:
        if tool_name == "find_hidden_links":
            entity = tool_args.get("entity_name", debtor_name)
            return find_hidden_links.invoke({"entity_name": entity})

        elif tool_name == "detect_fraud_rings":
            return detect_fraud_rings.invoke({})

        elif tool_name == "find_layering_patterns":
            entity = tool_args.get("entity_name", debtor_name)
            return find_layering_patterns.invoke({"entity_name": entity})

        elif tool_name == "check_behavioral_drift":
            entity = tool_args.get("entity_id", debtor_name)
            return check_behavioral_drift.invoke({"entity_id": entity})

        elif tool_name == "analyze_transaction_topology":
            return analyze_transaction_topology.invoke({"uetr": uetr})

        elif tool_name == "get_entity_profile":
            entity = tool_args.get("entity_id", debtor_name)
            return get_entity_profile.invoke({"entity_id": entity})

        elif tool_name == "get_investigation_history":
            entity = tool_args.get("entity_id", debtor_name)
            return get_investigation_history.invoke({"entity_id": entity})

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
    hidden_links: List[Dict],
    graph_risk_score: float,
) -> float:
    """Process tool results and update findings and risk score.

    Args:
        tool_name: Name of the executed tool
        tool_result: Result from the tool
        findings: List to append findings to (modified in place)
        hidden_links: List to append hidden link data (modified in place)
        graph_risk_score: Current graph risk score

    Returns:
        Updated graph risk score
    """
    if not tool_result or "error" in tool_result:
        return graph_risk_score

    if tool_name == "find_hidden_links":
        if tool_result.get("has_hidden_links"):
            paths = tool_result.get("paths", [])
            hidden_links.extend(paths)
            graph_risk_score = max(graph_risk_score, 0.85)
            findings.append(
                f"HIDDEN LINK TO HIGH-RISK ENTITY: Found {len(paths)} connection path(s) "
                f"to sanctioned or watchlisted entities. Risk entity: {tool_result.get('risk_entity', 'Unknown')}"
            )

    elif tool_name == "detect_fraud_rings":
        if tool_result.get("high_risk"):
            graph_risk_score = max(graph_risk_score, 0.9)
            ring_count = tool_result.get("ring_count", 0)
            findings.append(
                f"FRAUD RING MEMBERSHIP: Entity is part of {ring_count} potential fraud ring structure(s). "
                f"Ring members include known high-risk entities."
            )

    elif tool_name == "find_layering_patterns":
        if tool_result.get("layering_risk") == "high":
            graph_risk_score = max(graph_risk_score, 0.85)
            cycle_count = tool_result.get("cycle_count", 0)
            findings.append(
                f"LAYERING PATTERN DETECTED: Found {cycle_count} circular money flow pattern(s) "
                f"consistent with money laundering layering techniques."
            )

    elif tool_name == "check_behavioral_drift":
        if tool_result.get("drift_detected"):
            drift_score = tool_result.get("drift_score", 0)
            graph_risk_score = max(graph_risk_score, 0.7)
            findings.append(
                f"BEHAVIORAL ANOMALY: Entity shows significant deviation from historical baseline. "
                f"Drift score: {drift_score:.2f}. Anomalies: {tool_result.get('anomalies', [])}"
            )

    elif tool_name == "get_entity_profile":
        risk_flags = tool_result.get("risk_flags", [])
        if risk_flags:
            graph_risk_score = max(graph_risk_score, 0.7)
            findings.append(
                f"ENTITY RISK FLAGS: {len(risk_flags)} risk indicator(s) found: {', '.join(risk_flags[:5])}"
            )

    elif tool_name == "get_investigation_history":
        if tool_result.get("has_prior_issues"):
            graph_risk_score = max(graph_risk_score, 0.8)
            prior_count = tool_result.get("prior_investigation_count", 0)
            findings.append(
                f"PRIOR INVESTIGATION HISTORY: Entity has {prior_count} prior suspicious activity report(s) "
                f"or investigation(s) on record."
            )

    return graph_risk_score


def prosecutor_agent(state: AgentState) -> Dict[str, Any]:
    """The Prosecutor agent - aggressively seeks fraud evidence.

    This agent is responsible for investigating transactions for potential
    financial crimes. It uses a variety of graph-based and behavioral tools
    to identify suspicious patterns and connections.

    Args:
        state: Current investigation state containing transaction details
               and any prior debate messages

    Returns:
        State update dictionary containing:
        - prosecutor_findings: List of evidence findings
        - messages: Debate message from prosecutor
        - tool_calls: Record of all tool invocations
        - graph_context: Accumulated graph analysis results
        - hidden_links: Any hidden entity connections found
        - graph_risk_score: Calculated risk score from graph analysis
        - current_phase: Next phase indicator
    """
    logger.info(
        f"Prosecutor agent starting investigation for UETR: {state.get('uetr', 'Unknown')}"
    )

    llm = get_prosecutor_llm()
    tools = [
        find_hidden_links,
        detect_fraud_rings,
        analyze_transaction_topology,
        find_layering_patterns,
        check_behavioral_drift,
        get_entity_profile,
        get_investigation_history,
    ]

    # Extract transaction context
    iso_message = state.get("iso_message", {})
    debtor_name = iso_message.get("debtor", {}).get("name", "Unknown Debtor")
    creditor_name = iso_message.get("creditor", {}).get("name", "Unknown Creditor")
    amount = iso_message.get("amount", {})
    uetr = state.get("uetr", "")
    purpose_code = iso_message.get("purpose_code", "N/A")
    remittance_info = iso_message.get("remittance_info", {})

    # Build debate history context
    message_history = state.get("messages", [])
    history_text = ""
    if message_history:
        history_text = "\n## PRIOR DEBATE CONTEXT\n"
        for msg in message_history[-6:]:  # Last 6 messages for context
            speaker = msg.get("speaker", "unknown").upper()
            content = msg.get("content", "")
            # Truncate long messages for context window efficiency
            if len(content) > 300:
                content = content[:300] + "... [truncated]"
            history_text += f"**{speaker}**: {content}\n\n"

    # Construct investigation prompt
    investigation_prompt = f"""## TRANSACTION UNDER INVESTIGATION

| Field | Value |
|-------|-------|
| UETR | `{uetr}` |
| Debtor (Originator) | {debtor_name} |
| Creditor (Beneficiary) | {creditor_name} |
| Amount | {amount.get("value", "0")} {amount.get("currency", "EUR")} |
| Purpose Code | {purpose_code} |
| Remittance Information | {remittance_info} |

**Investigation Round**: {state.get("round_count", 1)} of 3
{history_text}

## YOUR MISSION
Conduct a thorough investigation of this transaction. Use ALL relevant tools to:

1. Check BOTH parties (debtor and creditor) for hidden links to sanctioned entities
2. Analyze fraud ring membership
3. Detect layering patterns
4. Check for behavioral drift from historical baselines
5. Review any prior investigation history

Document every finding with evidence IDs. Be aggressive but evidence-based.
Focus on MATERIAL findings that would concern a compliance officer.
"""

    messages = [
        SystemMessage(content=PROSECUTOR_SYSTEM_PROMPT),
        HumanMessage(content=investigation_prompt),
    ]

    # Initialize tracking variables
    findings: List[str] = []
    graph_context = ""
    hidden_links: List[Dict] = []
    graph_risk_score = 0.0
    executed_tool_calls: List[Dict] = []

    # Invoke LLM with tools
    try:
        response = invoke_with_fallback(llm, messages, tools)
    except Exception as e:
        logger.error(f"LLM invocation failed: {e}")
        # Return minimal state update on failure
        return {
            "prosecutor_findings": [f"Investigation error: {str(e)}"],
            "messages": [
                {
                    "speaker": "prosecutor",
                    "content": f"Investigation encountered an error: {str(e)}. Unable to complete analysis.",
                    "evidence_ids": [],
                    "timestamp": datetime.now().isoformat(),
                }
            ],
            "tool_calls": [],
            "current_phase": "rebuttal",
        }

    # Process tool calls
    if hasattr(response, "tool_calls") and response.tool_calls:
        for tool_call in response.tool_calls:
            tool_name = tool_call.get("name", "")
            tool_args = tool_call.get("args", {})

            logger.debug(f"Executing tool: {tool_name} with args: {tool_args}")

            # Execute the tool
            tool_result = _execute_tool(tool_name, tool_args, debtor_name, uetr)

            if tool_result:
                # Process results and update risk score
                graph_risk_score = _process_tool_results(
                    tool_name, tool_result, findings, hidden_links, graph_risk_score
                )

                # Accumulate graph context
                graph_context += f"\n### {tool_name}\n{json.dumps(tool_result, default=str, indent=2)}\n"

            # Record tool call for audit trail
            executed_tool_calls.append(
                {
                    "agent": "prosecutor",
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

    # Generate evidence IDs for findings
    evidence_ids = [f"EVID-{i + 1:03d}" for i in range(len(findings))]

    # Create formal debate message
    debate_message: DebateMessage = {
        "speaker": "prosecutor",
        "content": final_content,
        "evidence_ids": evidence_ids,
        "timestamp": datetime.now().isoformat(),
    }

    logger.info(
        f"Prosecutor investigation complete. Findings: {len(findings)}, "
        f"Risk score: {graph_risk_score:.2f}, Hidden links: {len(hidden_links)}"
    )

    # Return state update
    return {
        "prosecutor_findings": findings,
        "messages": [debate_message],
        "tool_calls": executed_tool_calls,
        "graph_context": graph_context,
        "hidden_links": hidden_links,
        "graph_risk_score": graph_risk_score,
        "current_phase": "rebuttal",
    }
