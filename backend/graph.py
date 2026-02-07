from typing import Dict, Any, Literal
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from backend.models.state import AgentState
from backend.agents.prosecutor import prosecutor_agent
from backend.agents.skeptic import skeptic_agent
from backend.agents.judge import judge_agent


def should_continue_debate(state: AgentState) -> Literal["prosecutor", "end"]:
    """Determine if the debate should continue or conclude."""
    needs_more = state.get("needs_more_evidence", False)
    round_count = state.get("round_count", 1)
    confidence = state.get("confidence_score", 0.0)

    # Continue if:
    # 1. Judge explicitly requests more evidence
    # 2. Confidence is below threshold
    # 3. We haven't exceeded max rounds
    if needs_more and round_count <= 3 and confidence < 0.8:
        return "prosecutor"

    return "end"


def create_investigation_graph() -> StateGraph:
    """Create the LangGraph workflow for the investigation swarm."""

    # Initialize the graph with our state schema
    workflow = StateGraph(AgentState)

    # Add nodes for each agent
    workflow.add_node("prosecutor", prosecutor_agent)
    workflow.add_node("skeptic", skeptic_agent)
    workflow.add_node("judge", judge_agent)

    # Define the flow
    # Start -> Prosecutor
    workflow.set_entry_point("prosecutor")

    # Prosecutor -> Skeptic (always)
    workflow.add_edge("prosecutor", "skeptic")

    # Skeptic -> Judge (always)
    workflow.add_edge("skeptic", "judge")

    # Judge -> conditional (continue or end)
    workflow.add_conditional_edges(
        "judge",
        should_continue_debate,
        {
            "prosecutor": "prosecutor",  # Loop back for more evidence
            "end": END,  # Conclude the investigation
        },
    )

    return workflow


def get_compiled_graph(checkpointer=None):
    """Get the compiled graph with optional checkpointer for persistence."""
    workflow = create_investigation_graph()

    if checkpointer is None:
        checkpointer = MemorySaver()

    return workflow.compile(checkpointer=checkpointer)


def create_initial_state(uetr: str, iso_message: Dict[str, Any]) -> AgentState:
    """Create the initial state for a new investigation."""
    return AgentState(
        uetr=uetr,
        iso_message=iso_message,
        graph_risk_score=0.0,
        semantic_risk_score=0.5,  # Start neutral
        historical_drift=0.0,
        prosecutor_findings=[],
        skeptic_findings=[],
        messages=[],
        graph_context="",
        hidden_links=[],
        doc_context="",
        alibi_evidence=[],
        drift_context="",
        behavioral_baseline={},
        verdict=None,
        risk_level="medium",  # Start at medium until investigated
        confidence_score=0.0,
        human_override=None,
        current_phase="investigation",
        round_count=1,
        needs_more_evidence=False,
    )


async def run_investigation(
    uetr: str, iso_message: Dict[str, Any], thread_id: str = None
) -> Dict[str, Any]:
    """Run a full investigation on a transaction.

    Args:
        uetr: Unique End-to-End Transaction Reference
        iso_message: Parsed ISO 20022 message
        thread_id: Optional thread ID for checkpointing

    Returns:
        Final state with verdict and all findings
    """
    graph = get_compiled_graph()
    initial_state = create_initial_state(uetr, iso_message)

    config = {"configurable": {"thread_id": thread_id or uetr}}

    # Run the graph
    final_state = None
    async for event in graph.astream(initial_state, config):
        # Track the latest state
        for node_name, node_state in event.items():
            final_state = node_state

    return final_state


def run_investigation_sync(
    uetr: str, iso_message: Dict[str, Any], thread_id: str = None
) -> Dict[str, Any]:
    """Synchronous version of run_investigation."""
    graph = get_compiled_graph()
    initial_state = create_initial_state(uetr, iso_message)

    config = {"configurable": {"thread_id": thread_id or uetr}}

    # Run the graph synchronously
    final_state = graph.invoke(initial_state, config)

    return final_state


# Export for easy import
__all__ = [
    "create_investigation_graph",
    "get_compiled_graph",
    "create_initial_state",
    "run_investigation",
    "run_investigation_sync",
]
