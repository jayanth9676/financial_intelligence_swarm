from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, Response
from pydantic import BaseModel
from typing import Optional, Dict, Any, List, AsyncGenerator
import json
import os
import logging
from datetime import datetime
import random
import uuid
import time

from backend.graph import create_initial_state, get_compiled_graph
from backend.tools.tools_iso import parse_pacs008, parse_pain001, parse_camt053
from backend.store import transactions_store, save_transactions, load_transactions

# Import Routers
from backend.routers import monitor, compliance, partners, reconciliation
from backend.routers.approval import router as approval_router, init_approval_queue

# Import PDF generator (optional - handles gracefully if reportlab not installed)
try:
    from backend.pdf_generator import generate_sar_pdf, generate_annex_iv_pdf

    PDF_GENERATION_AVAILABLE = True
except ImportError:
    PDF_GENERATION_AVAILABLE = False

# Configure logging - ensure output is flushed immediately
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler()  # Explicitly use StreamHandler for console output
    ],
    force=True,  # Reset any existing logging configuration
)
# Ensure uvicorn's default loggers don't suppress output
logging.getLogger("uvicorn").setLevel(logging.INFO)
logging.getLogger("uvicorn.access").setLevel(logging.INFO)
logging.getLogger("uvicorn.error").setLevel(logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Financial Intelligence Swarm API",
    description="AI-powered fraud detection using Prosecutor-Skeptic-Judge debate pattern",
    version="1.0.0",
)

# CORS for frontend - support environment-based origins
cors_origins = os.getenv(
    "CORS_ORIGINS", "http://localhost:3000,http://localhost:5173"
).split(",")
    
allow_vercel = os.getenv("ALLOW_VERCEL_ORIGINS", "true").lower() != "false"
vercel_origin_regex = os.getenv("VERCEL_ORIGIN_REGEX", r".*\\.vercel\\.app$") if allow_vercel else None

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_origin_regex=vercel_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Log configured CORS origins at startup so runtime env is visible in logs
logger.info(f"CORS origins configured: {cors_origins}; vercel_regex={vercel_origin_regex}")

# Production hardening middleware (error handling, rate limiting, security headers)
from backend.middleware import setup_production_middleware

setup_production_middleware(
    app,
    config={
        "rate_limit": 200,  # requests per minute
        "enable_rate_limit": True,
        "enable_logging": True,
    },
)

# WebSocket support for real-time updates
from backend.websocket_handler import setup_websocket_routes

setup_websocket_routes(app)

# Include Routers
app.include_router(monitor.router)
app.include_router(compliance.router)
app.include_router(partners.router)
app.include_router(reconciliation.router)
app.include_router(approval_router)


# Sample transactions for auto-seeding
SAMPLE_TRANSACTIONS = [
    {
        "uetr": "eb9a5c8e-2f3b-4c7a-9d1e-5f8a2b3c4d5e",
        "debtor": {"name": "Shell Company Alpha"},
        "creditor": {"name": "Offshore Holdings LLC"},
        "amount": {"value": "245000.00", "currency": "EUR"},
        "purpose": {
            "structured": {"code": "CORT"},
            "unstructured": "Consulting services Q1 2026",
        },
    },
    {
        "uetr": "fb155e7a-28af-4477-a973-3892c0e6eb85",
        "debtor": {"name": "Muller & Sons KG"},
        "creditor": {"name": "Salesforce.com"},
        "amount": {"value": "1292.67", "currency": "EUR"},
        "purpose": {
            "structured": {"code": "SUPP"},
            "unstructured": "CRM subscription monthly",
        },
    },
    {
        "uetr": "b33a927d-094d-4300-816d-8f2c9e0a1b2c",
        "debtor": {"name": "Muller & Sons KG"},
        "creditor": {"name": "AWS EMEA SARL"},
        "amount": {"value": "13836.82", "currency": "EUR"},
        "purpose": {
            "structured": {"code": "SUPP"},
            "unstructured": "Cloud infrastructure Q1",
        },
    },
]


@app.on_event("startup")
async def seed_sample_transactions():
    """Seed sample transactions on startup for demo purposes."""
    # Load existing data first
    load_transactions()

    logger.info("Seeding sample transactions...")
    seeded = False
    for tx in SAMPLE_TRANSACTIONS:
        uetr = tx["uetr"]
        if uetr not in transactions_store:
            transactions_store[uetr] = {
                "parsed_message": tx,
                "status": "pending",
                "created_at": datetime.now().isoformat(),
                "risk_level": None,
                "verdict": None,
            }
            logger.info(f"Seeded transaction: {uetr}")
            seeded = True

    if seeded:
        save_transactions()

    # Initialize approval queue from existing transactions
    init_approval_queue(transactions_store)

    logger.info(f"Seeded {len(SAMPLE_TRANSACTIONS)} sample transactions")


class IngestRequest(BaseModel):
    xml_content: str
    message_type: str = "pacs.008"


class InvestigateRequest(BaseModel):
    uetr: str
    restart: bool = False


class OverrideRequest(BaseModel):
    """Request body for human override."""

    action: str  # "approve", "block", "escalate"
    reason: Optional[str] = None


class TransactionResponse(BaseModel):
    uetr: str
    debtor: str
    creditor: str
    amount: float
    currency: str
    status: str
    risk_level: Optional[str] = None
    created_at: str


# Vercel AI SDK Data Stream Protocol helpers
# Using the prefix-based format that frontend expects: 0: for text, d: for data
def stream_text(text: str) -> str:
    """Format text for Vercel AI SDK stream (prefix 0:)"""
    return f"0:{json.dumps(text)}\n"


def stream_data(data: Dict[str, Any]) -> str:
    """Format data for Vercel AI SDK stream (prefix d:)"""
    return f"d:{json.dumps(data)}\n"


def stream_tool_call(tool_name: str, args: Dict[str, Any]) -> str:
    """Format tool call for Vercel AI SDK stream (prefix b:)"""
    return f"b:{json.dumps({'name': tool_name, 'args': args})}\n"


def stream_error(message: str) -> str:
    """Format error for Vercel AI SDK stream (prefix e:)"""
    return f"e:{json.dumps({'message': message})}\n"


@app.get("/")
async def root():
    return {
        "message": "Financial Intelligence Swarm API",
        "status": "operational",
        "endpoints": [
            "/monitor",
            "/compliance",
            "/partners",
            "/reconciliation",
            "/approval",
        ],
    }


@app.post("/ingest")
async def ingest_transaction(request: IngestRequest):
    """Ingest an ISO 20022 XML message."""
    try:
        # Parse based on message type
        if request.message_type == "pacs.008":
            parsed = parse_pacs008.invoke({"xml_content": request.xml_content})
        elif request.message_type == "pain.001":
            parsed = parse_pain001.invoke({"xml_content": request.xml_content})
        elif request.message_type == "camt.053":
            parsed = parse_camt053.invoke({"xml_content": request.xml_content})
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported message type: {request.message_type}",
            )

        if not parsed.get("parsed_successfully"):
            raise HTTPException(
                status_code=400, detail=f"Failed to parse XML: {parsed.get('error')}"
            )

        # Store the transaction
        uetr = (
            parsed.get("uetr")
            or parsed.get("message_id")
            or f"GEN-{datetime.now().timestamp()}"
        )
        transactions_store[uetr] = {
            "parsed_message": parsed,
            "status": "pending",
            "created_at": datetime.now().isoformat(),
            "risk_level": None,
            "verdict": None,
        }
        save_transactions()

        return {
            "success": True,
            "uetr": uetr,
            "message_type": request.message_type,
            "parsed": parsed,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/transactions")
async def list_transactions(status: Optional[str] = None, limit: int = 1000):
    """List all ingested transactions."""
    transactions = []
    for uetr, data in transactions_store.items():
        if status and data.get("status") != status:
            continue

        parsed = data.get("parsed_message", {})
        transactions.append(
            {
                "uetr": uetr,
                "debtor": parsed.get("debtor", {}).get("name", "Unknown"),
                "creditor": parsed.get("creditor", {}).get("name", "Unknown"),
                "amount": float(parsed.get("amount", {}).get("value", 0)),
                "currency": parsed.get("amount", {}).get("currency", "EUR"),
                "status": data.get("status", "unknown"),
                "risk_level": data.get("risk_level"),
                "created_at": data.get("created_at", ""),
            }
        )

    return {"transactions": transactions[:limit], "total": len(transactions)}


@app.get("/transactions/{uetr}")
async def get_transaction(uetr: str):
    """Get a specific transaction by UETR."""
    if uetr not in transactions_store:
        raise HTTPException(status_code=404, detail="Transaction not found")

    return transactions_store[uetr]


async def investigation_stream(
    uetr: str, restart: bool = False
) -> AsyncGenerator[str, None]:
    """Stream investigation progress using Vercel AI SDK Data Stream Protocol."""

    logger.info(f"Starting investigation for UETR: {uetr}")

    # Get the transaction
    if uetr not in transactions_store:
        logger.warning(f"Transaction not found: {uetr}")
        yield stream_text(f"Error: Transaction {uetr} not found")
        return

    tx_data = transactions_store[uetr]

    # Handle restart: clear status and result, generate new thread_id
    if restart:
        logger.info(f"Restarting investigation for {uetr}")
        tx_data["status"] = "pending"
        tx_data["risk_level"] = None
        tx_data["verdict"] = None
        if "investigation_result" in tx_data:
            del tx_data["investigation_result"]
        # Generate a new thread ID to ensure fresh graph state
        tx_data["thread_id"] = f"{uetr}_{int(time.time())}"
        save_transactions()
        yield stream_text("Investigation reset requested. Starting fresh analysis...")

    # If investigation is already completed, replay the results
    if tx_data.get("status") == "completed" and "investigation_result" in tx_data:
        logger.info(f"Replaying investigation for UETR: {uetr}")
        yield stream_text(f"Replaying investigation for UETR: {uetr}")
        yield stream_data({"type": "status", "status": "completed", "uetr": uetr})

        result = tx_data["investigation_result"]

        # Group messages by speaker and only show the last message from each agent
        # This prevents showing intermediate judge verdicts from multi-round debates
        messages = result.get("messages", [])
        tool_calls = result.get("tool_calls", [])

        # Get the last message from each speaker (prosecutor, skeptic, judge)
        # The final investigation result should only show the concluding messages
        last_messages_by_speaker = {}
        for msg in messages:
            speaker = msg.get("speaker", "")
            last_messages_by_speaker[speaker] = msg

        # Build events in the correct order: tool calls first (sorted by time),
        # then final messages in debate order (prosecutor -> skeptic -> judge)
        all_events = []

        # Add all tool calls as events (these show the investigation process)
        for tc in tool_calls:
            all_events.append(
                {
                    "event_type": "tool_call",
                    "timestamp": tc.get("timestamp", ""),
                    "order": 0,  # Tool calls come first
                    "data": {
                        "type": "tool_call",
                        "agent": tc.get("agent"),
                        "tool_name": tc.get("tool_name"),
                        "args": tc.get("tool_args"),
                        "result": tc.get("result"),
                        "timestamp": tc.get("timestamp"),
                    },
                }
            )

        # Sort tool calls by timestamp
        all_events.sort(key=lambda e: e.get("timestamp", ""))

        # Stream tool calls first
        for event in all_events:
            yield stream_data(event["data"])

        # Now stream the final messages in debate order
        debate_order = ["prosecutor", "skeptic", "judge"]
        for speaker in debate_order:
            if speaker in last_messages_by_speaker:
                msg = last_messages_by_speaker[speaker]
                yield stream_data(
                    {
                        "type": "message",
                        "speaker": msg.get("speaker"),
                        "content": msg.get("content"),
                        "evidence_ids": msg.get("evidence_ids", []),
                        "timestamp": msg.get("timestamp"),
                    }
                )

        # Stream graph
        hidden_links = result.get("hidden_links", [])
        if hidden_links:
            yield stream_data(
                {
                    "type": "graph",
                    "nodes": _extract_graph_nodes(hidden_links),
                    "links": _extract_graph_links(hidden_links),
                    "highlight_path": _extract_highlight_path(hidden_links),
                }
            )
        else:
            # Fallback graph
            tx_graph = _generate_transaction_graph(
                tx_data.get("parsed_message", {}), uetr
            )
            yield stream_data(
                {
                    "type": "graph",
                    "nodes": tx_graph["nodes"],
                    "links": tx_graph["links"],
                    "highlight_path": tx_graph["highlightPath"],
                }
            )

        # Stream verdict
        yield stream_data(
            {
                "type": "verdict",
                "verdict": result.get("verdict", {}).get("verdict", "REVIEW"),
                "risk_level": result.get("risk_level", "medium"),
                "confidence_score": result.get("confidence_score", 0.5),
                "reasoning": result.get("verdict", {}).get("reasoning", ""),
                "recommended_actions": result.get("verdict", {}).get(
                    "recommended_actions", []
                ),
                "eu_ai_act_compliance": result.get("verdict", {}).get(
                    "eu_ai_act_compliance", {}
                ),
                "round": result.get("round_count", 1),
            }
        )

        yield stream_text("Investigation replay complete.")
        yield stream_data(
            {
                "type": "complete",
                "uetr": uetr,
                "risk_level": result.get("risk_level"),
                "verdict": result.get("verdict"),
            }
        )
        return

    iso_message = tx_data.get("parsed_message", {})

    # Update status
    tx_data["status"] = "investigating"
    save_transactions()

    yield stream_text(f"Starting investigation for UETR: {uetr}")
    yield stream_data({"type": "status", "status": "investigating", "uetr": uetr})

    try:
        graph = get_compiled_graph()
        initial_state = create_initial_state(uetr, iso_message)

        # Use stored thread_id or default to UETR
        thread_id = tx_data.get("thread_id", uetr)
        config = {"configurable": {"thread_id": thread_id}}

        # Track final state as we stream (avoid re-invoking the graph)
        final_state = None
        graph_emitted = False

        # Stream events from the graph
        logger.info(f"Starting graph execution for {uetr}")
        async for event in graph.astream(initial_state, config):
            for node_name, node_state in event.items():
                logger.info(f"[{node_name.upper()}] Processing node")

                # Track the latest state from each node
                if final_state is None:
                    final_state = dict(initial_state)
                final_state.update(node_state)

                # Stream node execution
                yield stream_text(f"[{node_name.upper()}] Processing...")

                if node_name == "prosecutor":
                    findings = node_state.get("prosecutor_findings", [])
                    hidden_links = node_state.get("hidden_links", [])
                    messages = node_state.get("messages", [])
                    tool_calls = node_state.get("tool_calls", [])

                    # Stream tool calls first
                    for tc in tool_calls:
                        yield stream_data(
                            {
                                "type": "tool_call",
                                "agent": "prosecutor",
                                "tool_name": tc["tool_name"],
                                "args": tc["tool_args"],
                                "result": tc["result"],
                                "timestamp": tc["timestamp"],
                            }
                        )

                    # Stream as debate message for frontend
                    if messages:
                        last_msg = (
                            messages[-1] if isinstance(messages[-1], dict) else {}
                        )
                        yield stream_data(
                            {
                                "type": "message",
                                "speaker": "prosecutor",
                                "content": last_msg.get("content", str(findings)),
                                "evidence_ids": last_msg.get("evidence_ids", []),
                                "timestamp": last_msg.get(
                                    "timestamp", datetime.now().isoformat()
                                ),
                            }
                        )

                    yield stream_data(
                        {
                            "type": "prosecutor_findings",
                            "findings": findings,
                            "hidden_links": hidden_links,
                            "graph_risk_score": node_state.get("graph_risk_score", 0),
                        }
                    )

                    # Stream graph visualization data - always generate from transaction if no links
                    if hidden_links:
                        yield stream_data(
                            {
                                "type": "graph",
                                "nodes": _extract_graph_nodes(hidden_links),
                                "links": _extract_graph_links(hidden_links),
                                "highlight_path": _extract_highlight_path(hidden_links),
                            }
                        )
                        graph_emitted = True
                    elif not graph_emitted:
                        # Generate graph from transaction data
                        tx_graph = _generate_transaction_graph(iso_message, uetr)
                        yield stream_data(
                            {
                                "type": "graph",
                                "nodes": tx_graph["nodes"],
                                "links": tx_graph["links"],
                                "highlight_path": tx_graph["highlightPath"],
                            }
                        )
                        graph_emitted = True

                elif node_name == "skeptic":
                    findings = node_state.get("skeptic_findings", [])
                    alibi = node_state.get("alibi_evidence", [])
                    messages = node_state.get("messages", [])
                    tool_calls = node_state.get("tool_calls", [])

                    # Stream tool calls first
                    for tc in tool_calls:
                        yield stream_data(
                            {
                                "type": "tool_call",
                                "agent": "skeptic",
                                "tool_name": tc["tool_name"],
                                "args": tc["tool_args"],
                                "result": tc["result"],
                                "timestamp": tc["timestamp"],
                            }
                        )

                    # Stream as debate message for frontend
                    if messages:
                        # Get the last skeptic message
                        skeptic_msgs = [
                            m for m in messages if m.get("speaker") == "skeptic"
                        ]
                        if skeptic_msgs:
                            last_msg = skeptic_msgs[-1]
                            yield stream_data(
                                {
                                    "type": "message",
                                    "speaker": "skeptic",
                                    "content": last_msg.get("content", str(findings)),
                                    "evidence_ids": last_msg.get("evidence_ids", []),
                                    "timestamp": last_msg.get(
                                        "timestamp", datetime.now().isoformat()
                                    ),
                                }
                            )

                    yield stream_data(
                        {
                            "type": "skeptic_findings",
                            "findings": findings,
                            "alibi_evidence": alibi,
                            "semantic_risk_score": node_state.get(
                                "semantic_risk_score", 0
                            ),
                        }
                    )

                elif node_name == "judge":
                    verdict = node_state.get("verdict", {})
                    messages = node_state.get("messages", [])

                    # Stream as debate message for frontend
                    if messages:
                        judge_msgs = [
                            m for m in messages if m.get("speaker") == "judge"
                        ]
                        if judge_msgs:
                            last_msg = judge_msgs[-1]
                            yield stream_data(
                                {
                                    "type": "message",
                                    "speaker": "judge",
                                    "content": last_msg.get(
                                        "content", json.dumps(verdict)
                                    ),
                                    "evidence_ids": last_msg.get("evidence_ids", []),
                                    "timestamp": last_msg.get(
                                        "timestamp", datetime.now().isoformat()
                                    ),
                                }
                            )

                    # Stream verdict with all details frontend expects
                    yield stream_data(
                        {
                            "type": "verdict",
                            "verdict": verdict.get("verdict", "REVIEW"),
                            "risk_level": node_state.get("risk_level", "medium"),
                            "confidence_score": node_state.get("confidence_score", 0.5),
                            "reasoning": verdict.get("reasoning", ""),
                            "recommended_actions": verdict.get(
                                "recommended_actions", []
                            ),
                            "eu_ai_act_compliance": verdict.get(
                                "eu_ai_act_compliance",
                                {
                                    "article_13_satisfied": True,
                                    "transparency_statement": "Generated by FIS Swarm AI",
                                    "human_oversight_required": True,
                                },
                            ),
                            "round": node_state.get("round_count", 1),
                        }
                    )

                    # Check if continuing
                    if node_state.get("needs_more_evidence"):
                        yield stream_text(
                            f"Requesting additional evidence (Round {node_state.get('round_count', 1)})"
                        )

        # Use tracked final state (no duplicate invocation)
        if final_state is None:
            final_state = initial_state

        # Update transaction store
        tx_data["status"] = "completed"
        tx_data["risk_level"] = final_state.get("risk_level")
        tx_data["verdict"] = final_state.get("verdict")
        tx_data["investigation_result"] = final_state
        save_transactions()

        # Add to approval queue if completed
        # We need to manually call this here because main.py doesn't automatically watch for changes
        # In a real app, this would be an event listener
        from backend.routers.approval import add_to_approval_queue

        parsed = tx_data.get("parsed_message", {})
        amount = parsed.get("amount", {})
        add_to_approval_queue(
            uetr=uetr,
            amount=float(amount.get("value", 0)),
            currency=amount.get("currency", "EUR"),
            risk_level=final_state.get("risk_level", "medium"),
            debtor=parsed.get("debtor", {}).get("name", "Unknown"),
            creditor=parsed.get("creditor", {}).get("name", "Unknown"),
            investigation_result=final_state.get("verdict"),
        )

        logger.info(
            f"Investigation complete for {uetr}: verdict={final_state.get('verdict', {}).get('verdict', 'N/A')}, risk={final_state.get('risk_level')}"
        )

        yield stream_text("Investigation complete.")
        yield stream_data(
            {
                "type": "complete",
                "uetr": uetr,
                "risk_level": final_state.get("risk_level"),
                "verdict": final_state.get("verdict"),
            }
        )

    except Exception as e:
        logger.error(f"Investigation error for {uetr}: {e}", exc_info=True)
        tx_data["status"] = "error"
        yield stream_text(f"Error during investigation: {str(e)}")
        yield stream_data({"type": "error", "message": str(e)})


def _extract_graph_nodes(hidden_links: List[Dict]) -> List[Dict]:
    """Extract nodes for graph visualization."""
    nodes = {}
    for link in hidden_links:
        path_nodes = link.get("path_nodes", link.get("path", []))
        risk_entity = link.get("risk_entity", link.get("end", ""))
        for node_name in path_nodes:
            if node_name not in nodes:
                # Determine node type based on position and risk
                is_sanctioned = (
                    node_name == risk_entity or "sanctioned" in node_name.lower()
                )
                nodes[node_name] = {
                    "id": node_name,
                    "name": node_name,
                    "type": "sanctioned" if is_sanctioned else "entity",
                    "riskScore": 1.0 if is_sanctioned else 0.5,
                }
    return list(nodes.values())


def _extract_graph_links(hidden_links: List[Dict]) -> List[Dict]:
    """Extract links for graph visualization."""
    links = []
    for link in hidden_links:
        path_nodes = link.get("path_nodes", link.get("path", []))
        for i in range(len(path_nodes) - 1):
            links.append({"source": path_nodes[i], "target": path_nodes[i + 1]})
    return links


def _extract_highlight_path(hidden_links: List[Dict]) -> List[str]:
    """Extract node IDs for highlighting the suspicious path."""
    all_nodes = []
    for link in hidden_links:
        path_nodes = link.get("path_nodes", link.get("path", []))
        all_nodes.extend(path_nodes)
    return list(set(all_nodes))


def _generate_transaction_graph(
    iso_message: Dict[str, Any], uetr: str
) -> Dict[str, Any]:
    """Generate graph visualization data from transaction ISO message."""
    debtor = iso_message.get("debtor", {})
    creditor = iso_message.get("creditor", {})
    amount = iso_message.get("amount", {})

    debtor_name = debtor.get("name", "Unknown Debtor")
    creditor_name = creditor.get("name", "Unknown Creditor")

    nodes = [
        {
            "id": debtor_name,
            "name": debtor_name,
            "type": "entity",
            "riskScore": 0.3,
        },
        {
            "id": uetr,
            "name": f"{amount.get('value', '?')} {amount.get('currency', 'EUR')}",
            "type": "transaction",
            "riskScore": 0.5,
        },
        {
            "id": creditor_name,
            "name": creditor_name,
            "type": "entity",
            "riskScore": 0.3,
        },
    ]

    # Add account nodes if available
    if debtor.get("account"):
        nodes.append(
            {
                "id": f"acc_{debtor.get('account')[:8]}",
                "name": debtor.get("account", "")[:16] + "...",
                "type": "account",
                "riskScore": 0.2,
            }
        )

    if creditor.get("account"):
        nodes.append(
            {
                "id": f"acc_{creditor.get('account')[:8]}",
                "name": creditor.get("account", "")[:16] + "...",
                "type": "account",
                "riskScore": 0.2,
            }
        )

    links = [
        {"source": debtor_name, "target": uetr, "type": "SENT_FUNDS"},
        {"source": uetr, "target": creditor_name, "type": "RECEIVED_FUNDS"},
    ]

    # Add account links if accounts exist
    if debtor.get("account"):
        links.append(
            {
                "source": debtor_name,
                "target": f"acc_{debtor.get('account')[:8]}",
                "type": "HAS_ACCOUNT",
            }
        )
    if creditor.get("account"):
        links.append(
            {
                "source": creditor_name,
                "target": f"acc_{creditor.get('account')[:8]}",
                "type": "HAS_ACCOUNT",
            }
        )

    return {
        "nodes": nodes,
        "links": links,
        "highlightPath": [debtor_name, uetr, creditor_name],
    }


@app.post("/investigate")
async def investigate_transaction(request: InvestigateRequest):
    """Start an investigation on a transaction with streaming response."""
    return StreamingResponse(
        investigation_stream(request.uetr, request.restart),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Vercel-AI-UI-Message-Stream": "v1",
        },
    )


@app.post("/override/{uetr}")
async def human_override(uetr: str, request: OverrideRequest):
    """Human override of AI decision.

    Args:
        uetr: Transaction identifier
        request: Override request with action and optional reason
    """
    logger.info(
        f"Human override requested for {uetr}: action={request.action}, reason={request.reason}"
    )

    if uetr not in transactions_store:
        logger.warning(f"Override failed - transaction not found: {uetr}")
        raise HTTPException(status_code=404, detail="Transaction not found")

    tx_data = transactions_store[uetr]
    tx_data["human_override"] = {
        "action": request.action,
        "reason": request.reason or "",
        "timestamp": datetime.now().isoformat(),
    }
    tx_data["status"] = f"overridden_{request.action.lower()}"

    # Update risk level based on action
    if request.action == "approve":
        tx_data["risk_level"] = "low"
    elif request.action == "block":
        tx_data["risk_level"] = "critical"
    elif request.action == "escalate":
        tx_data["risk_level"] = "high"

    logger.info(
        f"Override applied for {uetr}: new_status={tx_data['status']}, new_risk={tx_data['risk_level']}"
    )
    save_transactions()

    return {
        "success": True,
        "uetr": uetr,
        "override": tx_data["human_override"],
        "new_status": tx_data["status"],
    }


# Also support POST /override with UETR in body for flexibility
@app.post("/override")
async def human_override_body(request: OverrideRequest, uetr: Optional[str] = None):
    """Human override of AI decision (alternative endpoint with UETR in query)."""
    if not uetr:
        raise HTTPException(status_code=400, detail="UETR is required")
    return await human_override(uetr, request)


class SARRequest(BaseModel):
    """Request body for SAR generation."""

    uetr: str
    include_evidence: bool = True


@app.post("/generate-sar/{uetr}")
async def generate_sar(uetr: str):
    """Generate a Suspicious Activity Report (SAR) for a blocked transaction.

    Args:
        uetr: Transaction identifier

    Returns:
        SAR document with transaction details and investigation findings
    """
    logger.info(f"SAR generation requested for {uetr}")

    if uetr not in transactions_store:
        raise HTTPException(status_code=404, detail="Transaction not found")

    tx_data = transactions_store[uetr]
    iso_message = tx_data.get("parsed_message", {})
    investigation = tx_data.get("investigation_result", {})
    verdict = tx_data.get("verdict", {})

    debtor = iso_message.get("debtor", {})
    creditor = iso_message.get("creditor", {})
    amount = iso_message.get("amount", {})

    # Build SAR content
    sar = {
        "report_id": f"SAR-{uetr[:8].upper()}",
        "generated_at": datetime.now().isoformat(),
        "status": "DRAFT",
        "transaction_details": {
            "uetr": uetr,
            "date": iso_message.get("creation_date", tx_data.get("created_at", "")),
            "amount": f"{amount.get('value', 0)} {amount.get('currency', 'EUR')}",
            "originator": {
                "name": debtor.get("name", "Unknown"),
                "account": debtor.get("account", "N/A"),
                "address": debtor.get("address", "N/A"),
            },
            "beneficiary": {
                "name": creditor.get("name", "Unknown"),
                "account": creditor.get("account", "N/A"),
                "address": creditor.get("address", "N/A"),
            },
            "purpose": iso_message.get("remittance_info", "Not specified"),
        },
        "risk_assessment": {
            "risk_level": tx_data.get("risk_level", "unknown"),
            "verdict": verdict.get("verdict", "REVIEW")
            if isinstance(verdict, dict)
            else "REVIEW",
            "confidence_score": investigation.get("confidence_score", 0.5),
        },
        "investigation_summary": {
            "prosecutor_findings": investigation.get("prosecutor_findings", []),
            "skeptic_findings": investigation.get("skeptic_findings", []),
            "hidden_links_detected": len(investigation.get("hidden_links", [])) > 0,
            "graph_risk_score": investigation.get("graph_risk_score", 0),
            "semantic_risk_score": investigation.get("semantic_risk_score", 0),
        },
        "reasoning": verdict.get("reasoning", "") if isinstance(verdict, dict) else "",
        "recommended_actions": verdict.get("recommended_actions", [])
        if isinstance(verdict, dict)
        else [],
        "human_override": tx_data.get("human_override"),
        "compliance": {
            "eu_ai_act": {
                "article_13_satisfied": True,
                "transparency_statement": "This SAR was generated with AI assistance. Human oversight is required before submission.",
                "human_oversight_required": True,
            }
        },
    }

    logger.info(f"SAR generated for {uetr}: {sar['report_id']}")

    # Store SAR in transaction record
    tx_data["sar_report"] = sar
    save_transactions()

    return sar


@app.post("/submit-sar/{uetr}")
async def submit_sar(uetr: str):
    """Submit a SAR to the regulator (mock).

    Args:
        uetr: Transaction identifier
    """
    if uetr not in transactions_store:
        raise HTTPException(status_code=404, detail="Transaction not found")

    tx_data = transactions_store[uetr]
    if "sar_report" not in tx_data:
        raise HTTPException(
            status_code=400, detail="No SAR generated for this transaction"
        )

    # Update status
    sar = tx_data["sar_report"]
    sar["status"] = "FILED"
    sar["filed_at"] = datetime.now().isoformat()
    sar["regulator_id"] = f"REG-{datetime.now().strftime('%Y%m%d')}-{uetr[:4]}"

    logger.info(f"SAR filed for {uetr}: {sar['report_id']}")
    save_transactions()

    return {
        "success": True,
        "message": "SAR successfully filed with regulator",
        "sar_report": sar,
    }


@app.get("/generate-sar-pdf/{uetr}")
async def generate_sar_pdf_endpoint(uetr: str):
    """Generate a PDF version of the SAR report.

    Args:
        uetr: Transaction identifier
    """
    if not PDF_GENERATION_AVAILABLE:
        raise HTTPException(
            status_code=501,
            detail="PDF generation not available. Install reportlab: pip install reportlab",
        )

    if uetr not in transactions_store:
        raise HTTPException(status_code=404, detail="Transaction not found")

    tx_data = transactions_store[uetr]
    if "sar_report" not in tx_data:
        raise HTTPException(
            status_code=400,
            detail="No SAR generated for this transaction. Generate SAR first.",
        )

    try:
        pdf_bytes = generate_sar_pdf(tx_data["sar_report"])
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="SAR-{uetr[:8].upper()}.pdf"'
            },
        )
    except Exception as e:
        logger.error(f"PDF generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {str(e)}")


@app.get("/annex-iv/{uetr}")
async def get_annex_iv(uetr: str):
    """Generate Annex IV Technical Documentation for EU AI Act compliance.

    Args:
        uetr: Transaction identifier

    Returns:
        JSON with Annex IV documentation structure
    """
    if uetr not in transactions_store:
        raise HTTPException(status_code=404, detail="Transaction not found")

    tx_data = transactions_store[uetr]
    parsed = tx_data.get("parsed_message", {})
    result = tx_data.get("investigation_result", {})

    # Return structured Annex IV documentation
    return {
        "uetr": uetr,
        "generated_at": datetime.now().isoformat(),
        "system_description": {
            "name": "Financial Intelligence Swarm (FIS)",
            "type": "High-Risk AI System for Financial Fraud Detection",
            "version": "1.0.0",
            "agents": [
                {
                    "name": "Prosecutor",
                    "role": "Investigates suspicious patterns and hidden entity links",
                },
                {
                    "name": "Skeptic",
                    "role": "Searches for exculpatory evidence and payment justifications",
                },
                {
                    "name": "Judge",
                    "role": "Renders balanced verdict based on debate evidence",
                },
            ],
        },
        "intended_purpose": (
            "Assist financial institution compliance officers in detecting suspicious transactions "
            "that may indicate money laundering, fraud, or sanctions violations. "
            "All decisions require human oversight and approval."
        ),
        "technical_architecture": {
            "orchestration": "LangGraph multi-agent workflow",
            "graph_database": "Neo4j for entity relationship analysis",
            "vector_database": "Qdrant for semantic document search",
            "behavioral_memory": "Mem0 for baseline tracking",
            "llm_provider": "Google Gemini",
        },
        "risk_management": [
            "Multi-agent debate prevents single model bias",
            "All decisions traceable with evidence IDs",
            "Confidence scores indicate certainty levels",
            "Human override capability for all verdicts",
            "Complete audit trail of reasoning",
        ],
        "human_oversight": {
            "required": True,
            "description": (
                "Per EU AI Act Article 14, this system requires human oversight for all final decisions. "
                "The system provides recommendations but NEVER autonomously executes decisions."
            ),
        },
        "transaction_record": {
            "uetr": uetr,
            "originator": parsed.get("debtor", {}).get("name", "N/A"),
            "beneficiary": parsed.get("creditor", {}).get("name", "N/A"),
            "amount": f"{parsed.get('amount', {}).get('value', 'N/A')} {parsed.get('amount', {}).get('currency', 'EUR')}",
            "risk_level": result.get("risk_level", "N/A"),
            "verdict": result.get("verdict", {}).get("verdict", "N/A"),
            "confidence_score": result.get("confidence_score", 0),
        },
    }


@app.get("/annex-iv-pdf/{uetr}")
async def get_annex_iv_pdf(uetr: str):
    """Generate Annex IV Technical Documentation as PDF.

    Args:
        uetr: Transaction identifier
    """
    if not PDF_GENERATION_AVAILABLE:
        raise HTTPException(
            status_code=501,
            detail="PDF generation not available. Install reportlab: pip install reportlab",
        )

    if uetr not in transactions_store:
        raise HTTPException(status_code=404, detail="Transaction not found")

    tx_data = transactions_store[uetr]

    try:
        pdf_bytes = generate_annex_iv_pdf(uetr, tx_data)
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="AnnexIV-{uetr[:8].upper()}.pdf"'
            },
        )
    except Exception as e:
        logger.error(f"Annex IV PDF generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {str(e)}")


@app.post("/generate-synthetic-data")
async def generate_synthetic_data():
    """Generate and ingest synthetic transactions for testing."""
    new_transactions = []

    # Entity Lists
    HIGH_RISK_ENTITIES = [
        "Shell Company Alpha",
        "Offshore Holdings LLC",
        "Unknown Trading Ltd",
        "Crypto Assets Inc",
    ]
    SAFE_ENTITIES = [
        "Global Trade Corp",
        "Muller & Sons KG",
        "Salesforce.com",
        "AWS EMEA",
        "Siemens AG",
    ]

    all_generated_txs = []

    # 1. Critical Risk Case: High amount (>500k), High-risk purpose, High-risk entity
    uetr_crit = str(uuid.uuid4())
    tx_crit = {
        "uetr": uetr_crit,
        "debtor": {
            "name": random.choice(SAFE_ENTITIES),
            "account": f"IBAN{random.randint(10000000, 99999999)}",
        },
        "creditor": {
            "name": random.choice(HIGH_RISK_ENTITIES),
            "account": f"IBAN{random.randint(10000000, 99999999)}",
        },
        "amount": {
            "value": str(round(random.uniform(500001.0, 950000.0), 2)),
            "currency": "USD",
        },
        "purpose": {
            "unstructured": "Consulting and Facilitation Services",
        },
        "creation_date": datetime.now().isoformat(),
    }
    all_generated_txs.append(tx_crit)

    # 2. High Risk Case: Shell company, Round amount (>50k)
    uetr_high = str(uuid.uuid4())
    # Round amount (e.g., 60000.00, 75000.00)
    amount_high = float(random.randint(50, 150)) * 1000.0
    tx_high = {
        "uetr": uetr_high,
        "debtor": {
            "name": random.choice(HIGH_RISK_ENTITIES),
            "account": f"IBAN{random.randint(10000000, 99999999)}",
        },
        "creditor": {
            "name": random.choice(SAFE_ENTITIES),  # Layering attempt?
            "account": f"IBAN{random.randint(10000000, 99999999)}",
        },
        "amount": {"value": str(amount_high), "currency": "EUR"},
        "purpose": {
            "unstructured": "Investment Fund Transfer",
        },
        "creation_date": datetime.now().isoformat(),
    }
    all_generated_txs.append(tx_high)

    # 3. Medium/Low Risk Cases (3 transactions)
    # Standard business transactions between safe entities
    LOW_RISK_PURPOSES = [
        "IT Equipment Purchase",
        "Cloud Hosting Fees",
        "Office Supplies",
        "Standard Consulting",
        "Legal Services Retainer",
    ]

    for _ in range(3):
        uetr = str(uuid.uuid4())
        debtor = random.choice(SAFE_ENTITIES)
        creditor = random.choice(SAFE_ENTITIES)
        # Ensure debtor != creditor
        while creditor == debtor:
            creditor = random.choice(SAFE_ENTITIES)

        amount = round(random.uniform(1000.0, 15000.0), 2)
        tx = {
            "uetr": uetr,
            "debtor": {
                "name": debtor,
                "account": f"IBAN{random.randint(10000000, 99999999)}",
            },
            "creditor": {
                "name": creditor,
                "account": f"IBAN{random.randint(10000000, 99999999)}",
            },
            "amount": {"value": str(amount), "currency": "EUR"},
            "purpose": {
                "unstructured": random.choice(LOW_RISK_PURPOSES),
            },
            "creation_date": datetime.now().isoformat(),
        }
        all_generated_txs.append(tx)

    # Process all generated transactions
    for tx in all_generated_txs:
        uetr = tx["uetr"]
        transactions_store[uetr] = {
            "parsed_message": tx,
            "status": "pending",
            "created_at": tx["creation_date"],
            "risk_level": None,
            "verdict": None,
        }

        # Flatten for response
        new_transactions.append(
            {
                "uetr": uetr,
                "debtor": tx["debtor"]["name"],
                "creditor": tx["creditor"]["name"],
                "amount": float(tx["amount"]["value"]),
                "currency": tx["amount"]["currency"],
                "status": "pending",
                "risk_level": None,
                "created_at": tx["creation_date"],
            }
        )

    save_transactions()
    return {"generated": len(new_transactions), "transactions": new_transactions}


@app.post("/clear-data")
async def clear_data():
    """Clear all transactions."""
    # We need to clear the dictionary in place, so the reference in store stays valid
    # or rely on the store functions if we had them.
    # Since simple import gives reference, clearing in place is safer.
    transactions_store.clear()
    save_transactions()
    return {"success": True, "message": "All data cleared"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
