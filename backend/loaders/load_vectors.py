"""Load data into Qdrant vector store."""

import json
import os
from typing import Any

from fastembed import TextEmbedding
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from backend.config import settings

DATA_RAW_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data", "data_raw")

_embedder = None


def get_client() -> QdrantClient:
    """Get Qdrant client."""
    return QdrantClient(
        url=settings.qdrant_url,
        api_key=settings.qdrant_api_key if settings.qdrant_api_key else None,
    )


def get_embedder() -> TextEmbedding:
    """Get embedding model singleton."""
    global _embedder
    if _embedder is None:
        _embedder = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
    return _embedder


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Generate embeddings for multiple texts."""
    embeddings = list(get_embedder().embed(texts))
    return [emb.tolist() for emb in embeddings]


def setup_collections(client: QdrantClient):
    """Create required collections if they don't exist."""
    vector_size = 384  # bge-small-en-v1.5

    collections = {
        "evidence": "Company documents, annual reports, business records",
        "regulations": "EU AI Act, AML regulations, compliance documents",
        "news": "Adverse media, news articles, press releases",
    }

    existing = {c.name for c in client.get_collections().collections}

    for name, description in collections.items():
        if name not in existing:
            client.create_collection(
                collection_name=name,
                vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
            )
            print(f"Created collection: {name} ({description})")
        else:
            print(f"Collection exists: {name}")


def load_evidence_documents(client: QdrantClient):
    """Load evidence documents from annual reports and business records."""
    documents = []

    annual_report_path = os.path.join(
        DATA_RAW_DIR, "precision_parts_annual_report_2025.md"
    )
    if os.path.exists(annual_report_path):
        with open(annual_report_path, "r", encoding="utf-8") as f:
            content = f.read()

        documents.append(
            {
                "content": content,
                "entity_name": "Precision Parts Gmbh",
                "source": "annual_report_2025.md",
                "document_type": "annual_report",
            }
        )

        chunks = _chunk_document(
            content, "Precision Parts Gmbh", "annual_report", "annual_report_2025.md"
        )
        documents.extend(chunks)

    if not documents:
        print("No evidence documents found")
        return 0

    texts = [doc["content"] for doc in documents]
    embeddings = embed_texts(texts)

    points = [
        PointStruct(
            id=i,
            vector=embeddings[i],
            payload=documents[i],
        )
        for i in range(len(documents))
    ]

    client.upsert(collection_name="evidence", points=points)
    print(f"Loaded {len(documents)} evidence documents")
    return len(documents)


def load_regulations(client: QdrantClient):
    """Load regulatory documents."""
    documents = []

    eu_ai_act_path = os.path.join(DATA_RAW_DIR, "EU_AI_Act_Annex_IV.txt")
    if os.path.exists(eu_ai_act_path):
        with open(eu_ai_act_path, "r", encoding="utf-8") as f:
            content = f.read()

        articles = _parse_regulation_articles(content, "eu_ai_act")
        documents.extend(articles)

    aml_regulations = [
        {
            "content": "Article 14: Customer Due Diligence - Obliged entities shall apply CDD measures when establishing a business relationship.",
            "article": "Article 14",
            "title": "Customer Due Diligence",
            "regulation_type": "aml",
        },
        {
            "content": "Article 18: Enhanced Due Diligence - In cases of higher risk, obliged entities shall apply enhanced customer due diligence measures.",
            "article": "Article 18",
            "title": "Enhanced Due Diligence",
            "regulation_type": "aml",
        },
        {
            "content": "Article 33: Reporting Obligations - Obliged entities shall promptly report suspicious transactions to the FIU.",
            "article": "Article 33",
            "title": "Reporting Obligations",
            "regulation_type": "aml",
        },
    ]
    documents.extend(aml_regulations)

    if not documents:
        print("No regulation documents found")
        return 0

    texts = [doc["content"] for doc in documents]
    embeddings = embed_texts(texts)

    points = [
        PointStruct(
            id=i,
            vector=embeddings[i],
            payload=documents[i],
        )
        for i in range(len(documents))
    ]

    client.upsert(collection_name="regulations", points=points)
    print(f"Loaded {len(documents)} regulation documents")
    return len(documents)


def load_adverse_media(client: QdrantClient):
    """Load adverse media and news articles."""
    documents = []

    news_path = os.path.join(DATA_RAW_DIR, "adverse_media_enriched.json")
    if os.path.exists(news_path):
        with open(news_path, "r", encoding="utf-8") as f:
            news_data = json.load(f)

        for item in news_data:
            metadata = item.get("metadata", {})
            documents.append(
                {
                    "headline": item.get("text", ""),
                    "content": item.get("text", ""),
                    "source": metadata.get("source", "news"),
                    "date": metadata.get("date", "2026-02-03"),
                    "sentiment": "negative"
                    if metadata.get("risk") == "High"
                    else "neutral",
                    "entity_mentions": metadata.get("entities", []),
                }
            )

    sample_news = [
        {
            "headline": "European authorities investigate shell company networks",
            "content": "Regulators across Europe are intensifying efforts to uncover complex shell company structures used for money laundering.",
            "source": "Financial Times",
            "date": "2026-01-15",
            "sentiment": "negative",
            "entity_mentions": [],
        },
        {
            "headline": "New sanctions imposed on UAE-based trading firms",
            "content": "OFAC has added several UAE-based trading companies to the SDN list citing concerns over sanctions evasion.",
            "source": "Reuters",
            "date": "2026-01-20",
            "sentiment": "negative",
            "entity_mentions": ["Al-Ghazali"],
        },
        {
            "headline": "German manufacturing sector sees strong Q4 exports",
            "content": "German precision manufacturing firms reported robust export growth in Q4, with Precision Parts Gmbh among the top performers.",
            "source": "Handelsblatt",
            "date": "2026-01-28",
            "sentiment": "positive",
            "entity_mentions": ["Precision Parts Gmbh"],
        },
    ]
    documents.extend(sample_news)

    if not documents:
        print("No news documents found")
        return 0

    texts = [doc.get("content", doc.get("headline", "")) for doc in documents]
    embeddings = embed_texts(texts)

    points = [
        PointStruct(
            id=i,
            vector=embeddings[i],
            payload=documents[i],
        )
        for i in range(len(documents))
    ]

    client.upsert(collection_name="news", points=points)
    print(f"Loaded {len(documents)} news articles")
    return len(documents)


def _chunk_document(
    content: str,
    entity_name: str,
    doc_type: str,
    source: str,
    chunk_size: int = 500,
) -> list[dict[str, Any]]:
    """Split document into overlapping chunks."""
    chunks = []
    lines = content.split("\n")
    current_chunk = []
    current_len = 0

    for line in lines:
        if current_len + len(line) > chunk_size and current_chunk:
            chunk_text = "\n".join(current_chunk)
            chunks.append(
                {
                    "content": chunk_text,
                    "entity_name": entity_name,
                    "source": source,
                    "document_type": doc_type,
                    "chunk_index": len(chunks),
                }
            )
            current_chunk = current_chunk[-2:] if len(current_chunk) > 2 else []
            current_len = sum(len(c) for c in current_chunk)

        current_chunk.append(line)
        current_len += len(line)

    if current_chunk:
        chunk_text = "\n".join(current_chunk)
        chunks.append(
            {
                "content": chunk_text,
                "entity_name": entity_name,
                "source": source,
                "document_type": doc_type,
                "chunk_index": len(chunks),
            }
        )

    return chunks


def _parse_regulation_articles(
    content: str, regulation_type: str
) -> list[dict[str, Any]]:
    """Parse regulation content into articles."""
    articles = []

    if "ARTICLE" in content.upper():
        parts = content.split("ARTICLE")
        for part in parts[1:]:
            lines = part.strip().split(":")
            if len(lines) >= 2:
                article_num = lines[0].strip()
                article_content = ":".join(lines[1:]).strip()
                articles.append(
                    {
                        "content": article_content,
                        "article": f"Article {article_num}",
                        "title": article_content[:50] + "..."
                        if len(article_content) > 50
                        else article_content,
                        "regulation_type": regulation_type,
                    }
                )
    else:
        articles.append(
            {
                "content": content,
                "article": "Full Text",
                "title": regulation_type.upper(),
                "regulation_type": regulation_type,
            }
        )

    return articles


def main():
    """Main loader function."""
    print("=" * 50)
    print("QDRANT VECTOR STORE LOADER")
    print("=" * 50)

    print("\nInitializing Qdrant connection...")
    client = get_client()

    try:
        client.get_collections()
        print("Connected to Qdrant successfully")
    except Exception as e:
        print(f"Failed to connect to Qdrant: {e}")
        return

    print("\nSetting up collections...")
    setup_collections(client)

    print("\nLoading evidence documents...")
    load_evidence_documents(client)

    print("\nLoading regulations...")
    load_regulations(client)

    print("\nLoading adverse media...")
    load_adverse_media(client)

    print("\nVector store loading complete!")


if __name__ == "__main__":
    main()
