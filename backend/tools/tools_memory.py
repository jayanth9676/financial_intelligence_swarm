from typing import Dict, Any, List
from langchain_core.tools import tool
from backend.config import settings
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# Singleton
_memory_client = None


def get_memory_client():
    """Get Mem0 client singleton. Returns None if API key not configured."""
    global _memory_client
    if _memory_client is None:
        if not settings.mem0_api_key:
            logger.info("Mem0 API key not configured - memory features disabled")
            return None
        try:
            from mem0 import MemoryClient

            _memory_client = MemoryClient(api_key=settings.mem0_api_key)
            logger.info("Mem0 client initialized successfully")
        except Exception as e:
            logger.warning(f"Failed to initialize Mem0 client: {e}")
            return None
    return _memory_client


def _safe_search(query: str, user_id: str, limit: int = 20) -> List[Dict[str, Any]]:
    """Safely search memories with proper error handling.

    Returns empty list if Mem0 is not configured or if search fails.
    """
    client = get_memory_client()
    if client is None:
        return []

    try:
        # Mem0 Platform API v2 uses filters instead of user_id parameter
        result = client.search(
            query=query,
            version="v2",
            filters={"user_id": user_id},
            limit=limit,
        )
        # New API returns {"results": [...]} or list
        if isinstance(result, dict):
            return result.get("results", result.get("memories", []))
        return result if isinstance(result, list) else []
    except TypeError:
        # Fallback - try with user_id as parameter for older API
        try:
            result = client.search(query=query, user_id=user_id, limit=limit)
            if isinstance(result, dict):
                return result.get("results", result.get("memories", []))
            return result if isinstance(result, list) else []
        except Exception as e:
            logger.debug(f"Mem0 search failed for {user_id}: {e}")
            return []
    except Exception as e:
        # Log but don't raise - memory is optional
        logger.debug(f"Mem0 search failed for {user_id}: {e}")
        return []


def _safe_get_all(user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    """Safely get all memories with proper error handling.

    Returns empty list if Mem0 is not configured or if request fails.
    """
    client = get_memory_client()
    if client is None:
        return []

    try:
        # Mem0 Platform API v2 uses filters for user_id
        result = client.get_all(
            version="v2",
            filters={"user_id": user_id},
            limit=limit,
        )
        # New API returns {"results": [...]}
        if isinstance(result, dict):
            return result.get("results", result.get("memories", []))
        return result if isinstance(result, list) else []
    except TypeError:
        # Fallback - try with user_id as direct parameter for older API
        try:
            result = client.get_all(user_id=user_id, limit=limit)
            if isinstance(result, dict):
                return result.get("results", [])
            return result if isinstance(result, list) else []
        except Exception as e:
            logger.debug(f"Mem0 get_all failed for {user_id}: {e}")
            return []
    except Exception as e:
        logger.debug(f"Mem0 get_all failed for {user_id}: {e}")
        return []


def _safe_add(messages: List[Dict], user_id: str, metadata: Dict) -> Dict[str, Any]:
    """Safely add memory with proper error handling."""
    client = get_memory_client()
    if client is None:
        return {"error": "Mem0 not configured", "finding_stored": False}

    try:
        # Mem0 Platform API v2 format
        result = client.add(
            messages=messages,
            user_id=user_id,
            metadata=metadata,
            version="v2",
        )
        return result if isinstance(result, dict) else {"id": "stored"}
    except TypeError:
        # Fallback - try without metadata/version for older API
        try:
            result = client.add(messages=messages, user_id=user_id)
            return result if isinstance(result, dict) else {"id": "stored"}
        except Exception as e:
            logger.debug(f"Mem0 add failed for {user_id}: {e}")
            return {"error": str(e), "finding_stored": False}
    except Exception as e:
        logger.debug(f"Mem0 add failed for {user_id}: {e}")
        return {"error": str(e), "finding_stored": False}


@tool
def check_behavioral_drift(entity_id: str) -> Dict[str, Any]:
    """Check for behavioral drift in an entity's transaction patterns.

    Compares recent behavior against historical baseline to detect anomalies.

    Args:
        entity_id: Unique identifier for the entity

    Returns:
        Dict with drift analysis including baseline vs current behavior
    """
    memories = _safe_search(
        query=f"behavioral patterns transaction history for {entity_id}",
        user_id=entity_id,
        limit=20,
    )

    baseline_memories = []
    recent_memories = []

    for mem in memories:
        memory_data = {
            "content": mem.get("memory", ""),
            "created_at": mem.get("created_at", ""),
            "metadata": mem.get("metadata", {}),
        }

        # Categorize by recency (simplified - in production use timestamps)
        if (
            "baseline" in mem.get("memory", "").lower()
            or "typical" in mem.get("memory", "").lower()
        ):
            baseline_memories.append(memory_data)
        else:
            recent_memories.append(memory_data)

    # Calculate drift indicators
    drift_detected = False
    drift_reasons = []

    # Check for sector changes
    baseline_sectors = [
        m for m in baseline_memories if "sector" in m["content"].lower()
    ]
    recent_sectors = [m for m in recent_memories if "sector" in m["content"].lower()]

    if baseline_sectors and recent_sectors:
        if baseline_sectors[0]["content"] != recent_sectors[0]["content"]:
            drift_detected = True
            drift_reasons.append("Sector shift detected")

    # Check for amount pattern changes - compare actual content
    baseline_amounts = [
        m for m in baseline_memories if "amount" in m["content"].lower()
    ]
    recent_amounts = [m for m in recent_memories if "amount" in m["content"].lower()]

    if baseline_amounts and recent_amounts:
        # Actually compare the content to detect drift
        baseline_content = baseline_amounts[0]["content"].lower()
        recent_content = recent_amounts[0]["content"].lower()
        if baseline_content != recent_content:
            drift_detected = True
            drift_reasons.append("Transaction amount pattern change")

    return {
        "entity_id": entity_id,
        "baseline_observations": len(baseline_memories),
        "recent_observations": len(recent_memories),
        "drift_detected": drift_detected,
        "drift_reasons": drift_reasons,
        "drift_score": 0.8 if drift_detected else 0.2,
        "baseline_summary": [m["content"] for m in baseline_memories[:3]],
        "recent_summary": [m["content"] for m in recent_memories[:3]],
    }


@tool
def get_entity_profile(entity_id: str) -> Dict[str, Any]:
    """Retrieve the complete behavioral profile for an entity.

    Args:
        entity_id: Unique identifier for the entity

    Returns:
        Dict with entity profile including typical behaviors and known facts
    """
    memories = _safe_get_all(user_id=entity_id, limit=50)

    profile = {
        "entity_id": entity_id,
        "facts": [],
        "typical_behaviors": [],
        "risk_flags": [],
        "relationships": [],
        "last_updated": None,
    }

    for mem in memories:
        content = mem.get("memory", "").lower()
        memory_entry = {
            "content": mem.get("memory", ""),
            "created_at": mem.get("created_at", ""),
        }

        if "typical" in content or "usually" in content or "baseline" in content:
            profile["typical_behaviors"].append(memory_entry)
        elif "risk" in content or "suspicious" in content or "flag" in content:
            profile["risk_flags"].append(memory_entry)
        elif "director" in content or "related" in content or "connected" in content:
            profile["relationships"].append(memory_entry)
        else:
            profile["facts"].append(memory_entry)

        # Track last update
        if mem.get("created_at"):
            if (
                profile["last_updated"] is None
                or mem["created_at"] > profile["last_updated"]
            ):
                profile["last_updated"] = mem["created_at"]

    profile["profile_completeness"] = (
        "complete" if len(profile["facts"]) > 5 else "partial"
    )

    return profile


@tool
def store_investigation_finding(
    entity_id: str, finding: str, finding_type: str = "observation"
) -> Dict[str, Any]:
    """Store a new finding from the investigation for future reference.

    Args:
        entity_id: Unique identifier for the entity
        finding: The finding to store
        finding_type: Type of finding (observation, risk_flag, exculpatory, verdict)

    Returns:
        Dict confirming the memory was stored
    """
    # Add metadata to the finding
    timestamped_finding = f"[{finding_type.upper()}] {finding}"

    result = _safe_add(
        messages=[{"role": "assistant", "content": timestamped_finding}],
        user_id=entity_id,
        metadata={
            "finding_type": finding_type,
            "timestamp": datetime.now().isoformat(),
        },
    )

    if "error" in result:
        return {
            "entity_id": entity_id,
            "finding_stored": False,
            "finding_type": finding_type,
            "error": result["error"],
        }

    return {
        "entity_id": entity_id,
        "finding_stored": True,
        "finding_type": finding_type,
        "memory_id": result.get("id", "unknown"),
    }


@tool
def compare_to_peer_group(
    entity_id: str, peer_type: str = "similar_industry"
) -> Dict[str, Any]:
    """Compare an entity's behavior to its peer group baseline.

    Args:
        entity_id: Unique identifier for the entity
        peer_type: Type of peer comparison (similar_industry, similar_size, similar_region)

    Returns:
        Dict with peer comparison analysis
    """
    # Get entity profile
    entity_memories = _safe_search(
        query=f"transaction patterns for {entity_id}",
        user_id=entity_id,
        limit=10,
    )

    # Get peer group baseline (in production, this would query a peer group)
    peer_memories = _safe_search(
        query=f"typical {peer_type} transaction patterns baseline",
        user_id="peer_baselines",
        limit=10,
    )

    # Simplified comparison
    entity_patterns = [m.get("memory", "") for m in entity_memories]
    peer_patterns = [m.get("memory", "") for m in peer_memories]

    # Check for deviations
    deviations = []
    if len(entity_patterns) > 0 and len(peer_patterns) > 0:
        # In production, use semantic similarity
        deviations.append("Comparison requires more data")

    return {
        "entity_id": entity_id,
        "peer_type": peer_type,
        "entity_observations": len(entity_patterns),
        "peer_observations": len(peer_patterns),
        "deviations": deviations,
        "within_peer_norms": len(deviations) == 0,
    }


@tool
def get_investigation_history(entity_id: str) -> Dict[str, Any]:
    """Retrieve the investigation history for an entity.

    Args:
        entity_id: Unique identifier for the entity

    Returns:
        Dict with past investigation findings and verdicts
    """
    memories = _safe_search(
        query=f"investigation verdict finding risk for {entity_id}",
        user_id=entity_id,
        limit=20,
    )

    investigations = []
    verdicts = []
    risk_flags = []

    for mem in memories:
        content = mem.get("memory", "")

        if "[VERDICT]" in content:
            verdicts.append(content)
        elif "[RISK_FLAG]" in content:
            risk_flags.append(content)
        elif "[OBSERVATION]" in content or "[EXCULPATORY]" in content:
            investigations.append(content)

    return {
        "entity_id": entity_id,
        "past_investigations": len(investigations),
        "past_verdicts": verdicts,
        "active_risk_flags": risk_flags,
        "investigation_details": investigations,
        "has_prior_issues": len(risk_flags) > 0
        or any("high risk" in v.lower() for v in verdicts),
    }
