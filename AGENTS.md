# AGENTS.md - Financial Intelligence Swarm (FIS)

## Commands

```bash
# Install
uv sync                                    # Python backend
cd frontend && npm install                 # Node.js frontend

# Run
uv run uvicorn backend.main:app --reload   # Backend (port 8000)
cd frontend && npm run dev                 # Frontend (port 3000)

# Test (IMPORTANT patterns)
uv run pytest                                              # All tests
uv run pytest tests/test_file.py -v                        # Single file
uv run pytest tests/test_file.py::TestClass::test_name -v  # Single test
uv run pytest -k "keyword" -v                              # Match keyword

# Lint (run before committing)
uv run ruff check . --fix        # Lint + auto-fix
uv run ruff format .             # Format
cd frontend && npm run lint      # TypeScript
```

## Architecture

**Stack:** Python 3.11+, LangGraph, FastAPI, Gemini, Next.js 16, TypeScript  
**DBs:** Neo4j (graph), Qdrant (vectors), Mem0 (memory)

```
START → Prosecutor → Skeptic → Judge → [needs_evidence?] → loop / END
```

**Directories:**
- `backend/agents/` - Prosecutor, Skeptic, Judge
- `backend/tools/` - `tools_graph.py`, `tools_docs.py`, `tools_memory.py`, `tools_iso.py`
- `backend/models/state.py` - `AgentState(TypedDict)` with Annotated reducers
- `frontend/src/lib/` - `api.ts`, `types.ts`
- `tests/conftest.py` - Shared fixtures

## Python Code Style

### Imports (ruff I001)
```python
from typing import Dict, Any, List, Optional  # 1. stdlib
from langchain_core.tools import tool          # 2. third-party
from backend.config import settings            # 3. local
```

### Type Hints (required)
```python
class AgentState(TypedDict):
    uetr: str
    risk_level: Literal["low", "medium", "high", "critical"]
    prosecutor_findings: Annotated[List[str], add]  # MUST use reducer

def process(uetr: str) -> Dict[str, Any]: ...
```

### Naming
| Element | Style | Example |
|---------|-------|---------|
| Files | snake_case | `tools_graph.py` |
| Classes | PascalCase | `AgentState` |
| Functions | snake_case | `find_hidden_links` |
| Constants | UPPER_SNAKE | `PROSECUTOR_SYSTEM_PROMPT` |

### Docstrings (Google style)
```python
@tool
def find_hidden_links(entity_name: str, max_hops: int = 3) -> Dict[str, Any]:
    """Find paths between entity and sanctioned parties.

    Args:
        entity_name: Entity to investigate.
        max_hops: Max relationship hops.

    Returns:
        Dict with paths and risk_score.
    """
```

### Error Handling
```python
# Tools: Return error dict, NEVER raise
@tool
def parse_pacs008(xml_content: str) -> Dict[str, Any]:
    try:
        return {"parsed_successfully": True, ...}
    except Exception as e:
        return {"parsed_successfully": False, "error": str(e)}

# FastAPI: Use HTTPException
raise HTTPException(status_code=400, detail=error_message)
```

### LangGraph State (CRITICAL)
```python
# List fields MUST use Annotated reducer to prevent overwrites
prosecutor_findings: Annotated[List[str], add]  # Correct
prosecutor_findings: List[str]                   # WRONG
```

### Neo4j
```python
# Parameterized queries only
session.run("MATCH (e:Entity {name: $name}) RETURN e", name=entity_name)
# Cleanup GDS projections
session.run(f"CALL gds.graph.drop('{graph_name}', false)")
```

## TypeScript (Frontend)

```typescript
"use client";
import React from "react";
import { motion } from "framer-motion";
import { investigateTransaction } from "@/lib/api";

interface Transaction {
  uetr: string;
  riskLevel: "low" | "medium" | "high" | "critical";
}
```

## Testing

```python
class TestClassName:
    def test_descriptive_name(self, fixture_name):
        result = function_under_test(input)
        assert result["key"] == expected_value

# Tool invocation
result = parse_pacs008.invoke({"xml_content": xml})
```

## Environment

`.env` (backend):
```
GOOGLE_API_KEY=           # Gemini
NEO4J_URI=bolt://localhost:7687
NEO4J_PASSWORD=
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=
MEM0_API_KEY=
```

`frontend/.env.local`:
```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Streaming Protocol

```python
def stream_text(text: str) -> str:
    return f"0:{json.dumps(text)}\n"

def stream_data(data: Dict[str, Any]) -> str:
    return f"d:{json.dumps(data)}\n"

# Types: "message", "verdict", "graph", "complete"
yield stream_data({"type": "message", "speaker": "prosecutor", ...})
```

## Compliance

- **EU AI Act:** Verdicts include `transparency_statement`, `human_oversight_required`
- **Audit:** Evidence IDs (EVID-*, DEF-*)
- **ISO 20022:** pacs.008, pain.001, camt.053 via `xmltodict`
