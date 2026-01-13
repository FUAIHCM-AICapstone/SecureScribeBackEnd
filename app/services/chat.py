import hashlib
import json
import re
import time
import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.crud.chat import crud_create_chat_message
from app.schemas.chat import Mention
from app.services.qdrant_service import (
    query_documents_by_file_id,
    query_documents_by_meeting_id,
    query_documents_by_project_id,
    semantic_search_with_filters,
)
from app.utils.llm import embed_documents, expand_query_with_llm
from app.utils.redis import get_async_redis_client


def create_chat_message(db: Session, conversation_id: uuid.UUID, user_id: uuid.UUID, content: str, message_type: str, mentions: Optional[List] = None):
    return crud_create_chat_message(db, conversation_id, user_id, content, message_type, mentions)


def _merge_context_candidates(candidates: List[Dict[str, Any]], limit: int) -> List[Dict[str, Any]]:
    """
    Deduplicate and rank document candidates by score while respecting a limit.
    """
    aggregated: Dict[str, Dict[str, Any]] = {}

    for idx, doc in enumerate(candidates, start=1):
        if isinstance(doc, dict):
            payload = doc.get("payload") or {}
            doc_id = doc.get("id")
            score = float(doc.get("score", 0.0) or 0.0)
            vector_data = doc.get("vector", [])
        else:
            payload = getattr(doc, "payload", {}) or {}
            doc_id = getattr(doc, "id", None)
            score = float(getattr(doc, "score", 0.0) or 0.0)
            vector_data = getattr(doc, "vector", [])

        if not isinstance(payload, dict):
            payload = {}

        file_id = payload.get("file_id")
        chunk_index = payload.get("chunk_index")
        if file_id is not None and chunk_index is not None:
            dedupe_key = f"{file_id}:{chunk_index}"
        elif doc_id is not None:
            dedupe_key = str(doc_id)
        else:
            digest_source = json.dumps(payload, sort_keys=True).encode("utf-8")
            digest = hashlib.sha256(digest_source).hexdigest()[:12]
            dedupe_key = f"fallback:{idx}:{digest}"

        existing = aggregated.get(dedupe_key)
        if existing is None or score > existing.get("score", 0.0):
            aggregated[dedupe_key] = {
                "id": doc_id if doc_id is not None else dedupe_key,
                "score": score,
                "payload": payload,
                "vector": vector_data,
                "key": dedupe_key,
            }

    if not aggregated:
        return []

    ordered = sorted(aggregated.values(), key=lambda item: item["score"], reverse=True)
    if limit > 0:
        ordered = ordered[:limit]
    return ordered


async def query_documents_for_mentions(
    mentions: List[Mention],
    current_user_id: Optional[str] = None,
    db: Optional[Session] = None,
    *,
    content: Optional[str] = None,
    top_k: int = 5,
    num_expansions: int = 3,
    include_query_expansion: bool = True,
) -> List[Dict[str, Any]]:
    """
    Query documents based on mentions, optionally augment with expansion search (if content is provided),
    and return a deduplicated list limited by top_k.
    """
    if not mentions:
        return []

    mention_results: List[Dict[str, Any]] = []

    for mention in mentions:
        entity_type = mention.entity_type
        entity_id = mention.entity_id

        if not entity_id:
            continue

        documents: List[dict] = []

        if entity_type == "meeting":
            documents = await query_documents_by_meeting_id(entity_id, top_k=top_k, db=db, user_id=current_user_id)
        elif entity_type == "project":
            documents = await query_documents_by_project_id(entity_id, top_k=top_k, db=db, user_id=current_user_id)
        elif entity_type == "file":
            documents = await query_documents_by_file_id(entity_id, top_k=top_k, db=db, user_id=current_user_id)
        else:
            # Unsupported mention types are ignored
            continue

        if documents:
            mention_results.extend(documents)

    expansion_results: List[Dict[str, Any]] = []
    normalized_content = (content or "").strip()
    if normalized_content and include_query_expansion:
        expansion_results = await perform_query_expansion_search(
            normalized_content,
            mentions=mentions,
            top_k=top_k,
            num_expansions=num_expansions,
        )

    combined = mention_results + expansion_results
    if not combined:
        return []

    return _merge_context_candidates(combined, limit=top_k)


async def perform_query_expansion_search(
    query: str,
    mentions: Optional[List[Mention]] = None,
    top_k: int = 5,
    num_expansions: int = 3,
) -> List[Dict[str, Any]]:
    """Orchestrate query expansion and semantic search."""
    try:
        print(f"Starting query expansion search for: '{query[:50]}...'")

        normalized_seed = re.sub(r"\s+", " ", (query or "").strip())
        if not normalized_seed:
            return []

        meeting_ids: List[str] = []
        project_ids: List[str] = []
        file_ids: List[str] = []
        entity_tokens: List[str] = []

        if mentions:
            for mention in mentions:
                if not mention.entity_id:
                    continue
                entity_id = str(mention.entity_id)
                if mention.entity_type == "meeting":
                    meeting_ids.append(entity_id)
                elif mention.entity_type == "project":
                    project_ids.append(entity_id)
                elif mention.entity_type == "file":
                    file_ids.append(entity_id)
                entity_tokens.append(entity_id)

        cache_key = None
        redis_client = None
        expanded_queries: List[str] = []
        try:
            redis_client = await get_async_redis_client()
        except Exception as redis_error:
            print(f"Redis unavailable for expansion cache: {redis_error}")
            redis_client = None

        if normalized_seed:
            hash_value = hashlib.sha256(normalized_seed.lower().encode("utf-8")).hexdigest()
            key_parts = [hash_value]
            if entity_tokens:
                key_parts.append("-".join(sorted(set(entity_tokens))))
            cache_key = f"expansion:{':'.join(key_parts)}"

        if redis_client and cache_key:
            try:
                cached_value = await redis_client.get(cache_key)
                if cached_value:
                    expanded_queries = json.loads(cached_value)
                    print("Expansion cache hit")
            except Exception as cache_error:
                print(f"Failed reading expansion cache: {cache_error}")
                expanded_queries = []

        if not expanded_queries:
            print("Expansion cache miss")
            expansion_start = time.perf_counter()
            expanded_queries = await expand_query_with_llm(query, num_expansions)
            expansion_duration = time.perf_counter() - expansion_start
            print(f"LLM expansion latency: {expansion_duration:.2f}s")
            if redis_client and cache_key and expanded_queries:
                try:
                    await redis_client.set(cache_key, json.dumps(expanded_queries), ex=86400)
                except Exception as cache_error:
                    print(f"Failed storing expansion cache: {cache_error}")
        else:
            print("Using cached expansion variants")

        if not expanded_queries:
            expanded_queries = [query]

        embed_start = time.perf_counter()
        embeddings = await embed_documents(expanded_queries)
        embed_duration = time.perf_counter() - embed_start
        print(f"Batch embedding latency: {embed_duration:.2f}s")

        if not embeddings:
            print("No embeddings produced for expansion queries")
            return []

        requested_top_k = max(top_k, 1)
        aggregated: Dict[str, Dict[str, Any]] = {}

        for idx, (expanded_query, vector) in enumerate(zip(expanded_queries, embeddings, strict=False), start=1):
            print(f"Searching with variant {idx}/{len(expanded_queries)}: '{expanded_query[:50]}...'")
            try:
                results = await semantic_search_with_filters(
                    query=expanded_query,
                    top_k=requested_top_k,
                    meeting_ids=meeting_ids or None,
                    project_ids=project_ids or None,
                    file_ids=file_ids or None,
                    query_vector=vector,
                )
            except Exception as search_error:
                print(f"Semantic search failed for variant {idx}: {search_error}")
                continue

            for doc in results:
                if isinstance(doc, dict):
                    payload = doc.get("payload") or {}
                    doc_id = doc.get("id")
                    score = float(doc.get("score", 0.0) or 0.0)
                    vector_data = doc.get("vector", [])
                else:
                    payload = getattr(doc, "payload", {}) or {}
                    doc_id = getattr(doc, "id", None)
                    score = float(getattr(doc, "score", 0.0) or 0.0)
                    vector_data = getattr(doc, "vector", [])

                if not isinstance(payload, dict):
                    payload = {}

                file_id = payload.get("file_id")
                chunk_index = payload.get("chunk_index")
                if file_id is not None and chunk_index is not None:
                    dedupe_key = f"{file_id}:{chunk_index}"
                elif doc_id is not None:
                    dedupe_key = str(doc_id)
                else:
                    digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()[:12]
                    dedupe_key = f"fallback:{idx}:{digest}"

                existing = aggregated.get(dedupe_key)
                if existing is None or score > existing.get("score", 0.0):
                    aggregated[dedupe_key] = {
                        "id": doc_id if doc_id is not None else dedupe_key,
                        "score": score,
                        "payload": payload,
                        "vector": vector_data,
                        "key": dedupe_key,
                    }

        if not aggregated:
            print("No documents retrieved from expansion variants")
            return []

        final_results = sorted(aggregated.values(), key=lambda item: item["score"], reverse=True)[:requested_top_k]
        print(f"Query expansion search completed: {len(final_results)} unique documents")
        return final_results

    except Exception as e:
        print(f"Query expansion search failed: {e}")
        return []
