from typing import List, Dict, Any
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Filter,
    FieldCondition,
    MatchValue,
    VectorParams,
    Distance,
)
from langchain_core.tools import tool
from backend.config import settings
import logging

logger = logging.getLogger(__name__)

# Singletons
_client = None
_embedder = None
_bedrock_client = None
_collections_initialized = False


def get_qdrant_client():
    global _client, _collections_initialized
    if _client is None:
        _client = QdrantClient(
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key if settings.qdrant_api_key else None,
        )

    # Initialize collections if not done
    if not _collections_initialized:
        _ensure_collections_exist(_client)
        _collections_initialized = True

    return _client


def _ensure_collections_exist(client: QdrantClient):
    """Ensure required Qdrant collections exist with correct schema."""
    # Get vector size from embedder (bge-small-en-v1.5 = 384 dimensions)
    vector_size = 384  # Default for BAAI/bge-small-en-v1.5

    collections = ["evidence", "news", "regulations"]

    for collection_name in collections:
        try:
            # Check if collection exists
            client.get_collection(collection_name)
            logger.debug(f"Collection '{collection_name}' already exists")
        except Exception:
            # Create collection if it doesn't exist
            try:
                client.create_collection(
                    collection_name=collection_name,
                    vectors_config=VectorParams(
                        size=vector_size,
                        distance=Distance.COSINE,
                    ),
                )
                logger.info(f"Created Qdrant collection: {collection_name}")
            except Exception as e:
                logger.warning(f"Could not create collection '{collection_name}': {e}")


def get_local_embedder():
    """Get local FastEmbed embedder."""
    global _embedder
    if _embedder is None:
        from fastembed import TextEmbedding

        _embedder = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
    return _embedder


def get_bedrock_client():
    """Get AWS Bedrock client for embeddings."""
    global _bedrock_client
    if _bedrock_client is None:
        import boto3

        _bedrock_client = boto3.client(
            "bedrock-runtime",
            region_name=settings.aws_region,
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
        )
    return _bedrock_client


def embed_text_local(text: str) -> List[float]:
    """Generate embedding using local FastEmbed."""
    embeddings = list(get_local_embedder().embed([text]))
    return embeddings[0].tolist()


def embed_text_bedrock(text: str) -> List[float]:
    """Generate embedding using AWS Bedrock Titan."""
    import json

    client = get_bedrock_client()
    model_id = settings.bedrock_embedding_model_id

    # Titan embedding request format
    body = json.dumps({"inputText": text})

    response = client.invoke_model(
        modelId=model_id,
        body=body,
        contentType="application/json",
        accept="application/json",
    )

    response_body = json.loads(response["body"].read())
    return response_body["embedding"]


def embed_text(text: str) -> List[float]:
    """Generate embedding for text using configured provider."""
    provider = settings.embedding_provider.lower()

    if provider == "bedrock" and settings.has_bedrock_credentials():
        try:
            return embed_text_bedrock(text)
        except Exception as e:
            # Fall back to local on error
            print(f"Bedrock embedding failed, falling back to local: {e}")
            return embed_text_local(text)
    else:
        return embed_text_local(text)


def _query_collection(
    collection_name: str,
    query_vector: List[float],
    query_filter: Filter = None,
    limit: int = 5,
) -> List[Dict[str, Any]]:
    """Query a Qdrant collection and return results with payload and scores.

    Uses the search API which is more stable across Qdrant versions.
    """
    client = get_qdrant_client()

    try:
        # Check if collection has any points
        collection_info = client.get_collection(collection_name)
        if collection_info.points_count == 0:
            logger.debug(f"Collection '{collection_name}' is empty")
            return []

        # Use the stable search API instead of query_points
        response = client.search(
            collection_name=collection_name,
            query_vector=query_vector,
            query_filter=query_filter,
            limit=limit,
            with_payload=True,
        )
        # search returns list of ScoredPoint
        results = []
        for point in response:
            results.append(
                {
                    "payload": point.payload or {},
                    "score": point.score if hasattr(point, "score") else 0.0,
                }
            )
        return results
    except Exception as e:
        # Return empty results on error (collection may not exist or be empty)
        logger.debug(f"Qdrant query failed for '{collection_name}': {e}")
        return []


@tool
def search_alibi(query: str, entity_name: str = None, limit: int = 5) -> Dict[str, Any]:
    """Search for exculpatory evidence in company documents, annual reports, and business records.

    Args:
        query: Search query describing the legitimate business explanation to find
        entity_name: Optional entity name to filter results
        limit: Maximum number of results to return

    Returns:
        Dict with matching evidence documents and relevance scores
    """
    query_vector = embed_text(query)

    search_filter = None
    if entity_name:
        search_filter = Filter(
            must=[
                FieldCondition(key="entity_name", match=MatchValue(value=entity_name))
            ]
        )

    results = _query_collection(
        collection_name="evidence",
        query_vector=query_vector,
        query_filter=search_filter,
        limit=limit,
    )

    evidence = []
    for hit in results:
        payload = hit["payload"]
        evidence.append(
            {
                "content": payload.get("content", ""),
                "source": payload.get("source", "unknown"),
                "document_type": payload.get("document_type", "unknown"),
                "relevance_score": hit["score"],
                "entity": payload.get("entity_name", "unknown"),
            }
        )

    return {
        "query": query,
        "results_found": len(evidence),
        "evidence": evidence,
        "has_alibi": any(e["relevance_score"] > 0.7 for e in evidence),
    }


@tool
def consult_regulation(
    query: str, regulation_type: str = "eu_ai_act"
) -> Dict[str, Any]:
    """Consult regulatory documents for compliance guidance.

    Args:
        query: The compliance question or context to search for
        regulation_type: Type of regulation to consult (eu_ai_act, aml, gdpr)

    Returns:
        Dict with relevant regulatory excerpts and article references
    """
    query_vector = embed_text(query)

    search_filter = Filter(
        must=[
            FieldCondition(
                key="regulation_type", match=MatchValue(value=regulation_type)
            )
        ]
    )

    results = _query_collection(
        collection_name="regulations",
        query_vector=query_vector,
        query_filter=search_filter,
        limit=3,
    )

    citations = []
    for hit in results:
        payload = hit["payload"]
        citations.append(
            {
                "article": payload.get("article", ""),
                "title": payload.get("title", ""),
                "content": payload.get("content", ""),
                "relevance_score": hit["score"],
            }
        )

    return {
        "query": query,
        "regulation_type": regulation_type,
        "citations": citations,
        "applicable_articles": [
            c["article"] for c in citations if c["relevance_score"] > 0.6
        ],
    }


@tool
def search_payment_justification(
    entity_name: str,
    amount_min: float = None,
    amount_max: float = None,
    purpose: str = None,
) -> Dict[str, Any]:
    """Search for documented payment justifications like authorized payment grids, contracts, or invoices.

    Args:
        entity_name: Name of the entity to search for
        amount_min: Optional minimum payment amount to filter
        amount_max: Optional maximum payment amount to filter
        purpose: Optional purpose description to match

    Returns:
        Dict with matching payment authorizations and business justifications
    """
    # Build semantic query
    query_parts = [f"authorized payments for {entity_name}"]
    if purpose:
        query_parts.append(f"purpose: {purpose}")
    if amount_min is not None and amount_max is not None:
        query_parts.append(f"amount range {amount_min} to {amount_max}")

    query = " ".join(query_parts)
    query_vector = embed_text(query)

    search_filter = Filter(
        must=[FieldCondition(key="entity_name", match=MatchValue(value=entity_name))]
    )

    results = _query_collection(
        collection_name="evidence",
        query_vector=query_vector,
        query_filter=search_filter,
        limit=5,
    )

    justifications = []
    for hit in results:
        payload = hit["payload"]
        content = payload.get("content", "")
        justifications.append(
            {
                "content": content,
                "source": payload.get("source", ""),
                "document_type": payload.get("document_type", ""),
                "relevance_score": hit["score"],
                "contains_payment_grid": "payment grid" in content.lower()
                or "authorized" in content.lower(),
            }
        )

    return {
        "entity": entity_name,
        "justifications_found": len(justifications),
        "justifications": justifications,
        "has_valid_authorization": any(
            j["contains_payment_grid"] and j["relevance_score"] > 0.7
            for j in justifications
        ),
    }


@tool
def search_adverse_media(entity_name: str) -> Dict[str, Any]:
    """Search for adverse media mentions related to an entity.

    Args:
        entity_name: Name of the entity to search

    Returns:
        Dict with adverse media hits and sentiment analysis
    """
    query = f"fraud scandal investigation {entity_name} money laundering sanctions"
    query_vector = embed_text(query)

    results = _query_collection(
        collection_name="news",
        query_vector=query_vector,
        limit=5,
    )

    media_hits = []
    for hit in results:
        payload = hit["payload"]
        media_hits.append(
            {
                "headline": payload.get("headline", ""),
                "source": payload.get("source", ""),
                "date": payload.get("date", ""),
                "sentiment": payload.get("sentiment", "neutral"),
                "relevance_score": hit["score"],
            }
        )

    negative_hits = [
        m
        for m in media_hits
        if m["sentiment"] == "negative" and m["relevance_score"] > 0.7
    ]

    return {
        "entity": entity_name,
        "total_hits": len(media_hits),
        "negative_hits": len(negative_hits),
        "media": media_hits,
        "adverse_media_risk": "high"
        if len(negative_hits) > 2
        else "low"
        if len(negative_hits) == 0
        else "medium",
    }
