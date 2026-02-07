# FIS: Financial Intelligence Swarm

**Tagline**: "Minority Report" for Financial Crime – Pre-crime detection via Agentic AI.

## 1. The Problem
Fraudsters layer. Rules fail (99% false positives). We need **investigation**, not just flagging.

## 2. The Solution
**FIS**: A multi-agent cognitive architecture.
*   **Ingest**: ISO 20022 & KYC Docs.
*   **Rebuild**: Money flow graph (Neo4j) + Semantic vector search (Qdrant).
*   **Debate**: Prosecutor (Accuse) vs. Skeptic (Defend) -> Judge (Verdict).

## 3. Live Demo (2 Min)
1.  **Alert**: $9k "Smurfing" tx to 'Global Consulting'. Rules miss it.
2.  **Prosecutor**: Finds 'Fan-In' pattern & sanctioned links via **Graph**.
3.  **Skeptic**: Finds "Annual Report" PDF via **Vector Search**. Argues pre-approval.
4.  **Judge**: Weighs evidence. **Verdict: ESCALATE** (Risk > Alibi). EU AI Act compliant.
5.  **GenUI**: Interactive graph generated instantly.

## 4. Value
*   **Compliance**: "White Box" decisions (EU AI Act Art. 13).
*   **Efficiency**: Auto-filter legitimate anomalies.
*   **Future**: Native ISO 20022 support.

## 5. Tech Stack
**Python, LangGraph, Neo4j, Qdrant, Mem0, FastAPI, Next.js 16.**

---
*Checklist: Docker up, Backend/Frontend running, Data loaded.*
