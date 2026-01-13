import logging
import mimetypes
import os
import re
import uuid
from typing import Any, Dict, List

from chonkie import CodeChunker, SentenceChunker
from qdrant_client import models as qmodels
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

from app.core.config import settings
from app.services.file import check_file_access, get_file
from app.services.meeting import get_meeting
from app.services.project import is_user_in_project
from app.utils.qdrant import get_qdrant_client


async def create_collection_if_not_exist(collection_name: str, dim: int) -> bool:
    """Create a collection if it doesn't exist.

    Args:
        collection_name: Name of the collection.
        dim: Vector dimension size.

    Returns:
        bool: True if created or already exists, False on error.
    """
    try:
        client = get_qdrant_client()
        existing_collections = [c.name for c in client.get_collections().collections]
        if collection_name in existing_collections:
            print(f"\033[94m[QDRANT] Collection {collection_name} already exists\033[0m")
            return False

        client.create_collection(
            collection_name=collection_name,
            vectors_config=qmodels.VectorParams(size=dim, distance=qmodels.Distance.COSINE),
        )
        print(f"\033[92m[QDRANT] Created collection {collection_name} with dim={dim}\033[0m")
        return True

    except Exception as e:
        print(f"\033[91m[QDRANT] Failed to create collection {collection_name}: {str(e)}\033[0m")
        logger.error(f"Create collection failed: {e}", exc_info=True)
        return False


async def upsert_vectors(collection: str, vectors: List[List[float]], payloads: List[Dict[str, Any]]) -> bool:
    """Upsert vectors to a collection with error handling.

    Args:
        collection: Collection name.
        vectors: List of embedding vectors.
        payloads: List of metadata payloads matching vectors.

    Returns:
        bool: True if successful, False otherwise.
    """
    if not vectors:
        return False

    try:
        client = get_qdrant_client()
        points = []
        for idx, vec in enumerate(vectors):
            point_id = str(uuid.uuid4())
            payload = payloads[idx] if idx < len(payloads) else {}
            points.append(qmodels.PointStruct(id=point_id, vector=vec, payload=payload))

        client.upsert(collection_name=collection, points=points, wait=True)
        print(f"\033[92m[QDRANT] Successfully upserted {len(points)} vectors to {collection}\033[0m")
        return True

    except Exception as e:
        print(f"\033[91m[QDRANT] Failed to upsert vectors: {str(e)}\033[0m")
        logger.error(f"Upsert vectors failed: {e}", exc_info=True)
        return False


async def search_vectors(
    collection: str,
    query_vector: List[float],
    top_k: int = 5,
    query_filter: qmodels.Filter | None = None,
) -> List[qmodels.ScoredPoint]:
    """Search for similar vectors in a collection with error handling.

    Args:
        collection: Collection name.
        query_vector: Query embedding vector.
        top_k: Number of results to return.
        query_filter: Optional Qdrant filter for results.

    Returns:
        List of scored points matching the query.
    """
    if not query_vector:
        return []

    try:
        client = get_qdrant_client()
        response = client.query_points(
            collection_name=collection,
            query=query_vector,
            limit=min(max(top_k, 1), 100),
            query_filter=query_filter,
            with_payload=True,
            with_vectors=True,
        )
        results = list(getattr(response, "points", response) or [])
        print(f"\033[92m[QDRANT] Search returned {len(results)} results from {collection}\033[0m")
        return results

    except Exception as e:
        print(f"\033[91m[QDRANT] Search failed: {str(e)}\033[0m")
        import logging

        logger = logging.getLogger(__name__)
        logger.error(f"Search vectors failed: {e}", exc_info=True)
        return []


async def semantic_search_with_filters(
    query: str,
    collection_name: str | None = None,
    top_k: int = 5,
    meeting_ids: List[str] | None = None,
    project_ids: List[str] | None = None,
    file_ids: List[str] | None = None,
    query_vector: List[float] | None = None,
) -> List[Dict[str, Any]]:
    """Perform semantic vector search with optional metadata filters.
    Args:
        query (str): The text query string for the search.
        collection_name (str | None): The name of the Qdrant collection.
        top_k (int): The number of results to return (default is 5).
        meeting_ids (List[str] | None): List of meeting IDs to filter results.
        project_ids (List[str] | None): List of project IDs to filter results.
        file_ids (List[str] | None): List of file IDs to filter results.
        query_vector (List[float] | None): The embedding vector of the query.
    Returns:
        List[Dict[str, Any]]: A list of found documents,
            each containing the fields: `id`, `score`, `payload`, `vector`.
    Notes:
        This function supports reusing an existing embedding vector (query_vector)
        to speed up searches, particularly useful for batch searches.
    """
    try:
        if not collection_name:
            collection_name = settings.QDRANT_COLLECTION_NAME
        # Generate query embedding
        if query_vector is None:
            from app.utils.llm import embed_query

            query_vector = await embed_query(query)

        if not query_vector:
            return []
        # Build filter conditions
        filter_conditions = []
        # Add meeting_ids filter (OR logic within meeting_ids)
        if meeting_ids:
            meeting_conditions = [qmodels.FieldCondition(key="meeting_id", match=qmodels.MatchValue(value=mid)) for mid in meeting_ids]
            if len(meeting_conditions) == 1:
                filter_conditions.append(meeting_conditions[0])
            else:
                filter_conditions.append(qmodels.Filter(should=meeting_conditions))
        # Add project_ids filter (OR logic within project_ids)
        if project_ids:
            project_conditions = [qmodels.FieldCondition(key="project_id", match=qmodels.MatchValue(value=pid)) for pid in project_ids]
            if len(project_conditions) == 1:
                filter_conditions.append(project_conditions[0])
            else:
                filter_conditions.append(qmodels.Filter(should=project_conditions))
        # Add file_ids filter (OR logic within file_ids)
        if file_ids:
            file_conditions = [qmodels.FieldCondition(key="file_id", match=qmodels.MatchValue(value=fid)) for fid in file_ids]
            if len(file_conditions) == 1:
                filter_conditions.append(file_conditions[0])
            else:
                filter_conditions.append(qmodels.Filter(should=file_conditions))
        # Combine all filters with AND logic
        query_filter = None
        if filter_conditions:
            query_filter = qmodels.Filter(must=filter_conditions)

        results = await search_vectors(
            collection=collection_name,
            query_vector=query_vector,
            top_k=top_k,
            query_filter=query_filter,
        )
        # Convert to consistent format
        documents: List[Dict[str, Any]] = []
        for result in results:
            doc = {
                "id": result.id,
                "score": float(result.score),
                "payload": result.payload or {},
                "vector": result.vector if hasattr(result, "vector") else [],
            }
            documents.append(doc)

        return documents

    except Exception:
        return []


def chunk_text(text: str, chunk_size: int = 1000) -> List[str]:
    """Chunk text using Chonkie: Code first, then sentences; 15% overlap; merge <200 tokens."""
    if not text:
        return []

    from collections import Counter

    # Parameters
    overlap_tokens = int(max(0, chunk_size) * 0.15)
    min_chunk_tokens = 200

    # Normalize and trim boilerplate
    text = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    line_counts = Counter(lines)
    boilerplate = {ln for ln, cnt in line_counts.items() if cnt > 2 and len(ln) < 200}
    if boilerplate:
        text_lines = [ln for ln in text.splitlines() if ln.strip() not in boilerplate]
        text = "\n".join(text_lines).strip()
    text = re.sub(r"[ \t]+", " ", text)

    # Extract code blocks into placeholders
    code_blocks: Dict[str, str] = {}

    def _code_repl(m: re.Match) -> str:
        idx = len(code_blocks)
        key = f"__CODE_BLOCK_{idx}__"
        code_blocks[key] = m.group(0)
        return f"\n{key}\n"

    text_no_code = re.sub(r"```.*?```", _code_repl, text, flags=re.DOTALL)

    # Prepare a simple Gemini-like token counter (run-first, minimal)
    def _gemini_token_counter(s: str) -> int:
        return len(s.split())

    # Initialize chunkers
    sent_chunker = SentenceChunker(
        tokenizer=_gemini_token_counter,
        chunk_size=chunk_size,
        chunk_overlap=overlap_tokens,
        min_sentences_per_chunk=1,
    )
    code_chunker = CodeChunker(
        language="markdown",
        tokenizer=_gemini_token_counter,
        chunk_size=chunk_size,
        include_nodes=False,
    )

    # Split back into prose vs placeholder segments preserving order
    placeholder_pattern = re.compile(r"__CODE_BLOCK_\d+__")
    segments: List[str] = []
    last = 0
    for m in placeholder_pattern.finditer(text_no_code):
        if m.start() > last:
            segments.append(text_no_code[last : m.start()])
        segments.append(m.group(0))
        last = m.end()
    if last < len(text_no_code):
        segments.append(text_no_code[last:])

    # Collect chunks with token counts for post-merge
    collected: List[Dict[str, Any]] = []
    for seg in segments:
        seg_str = seg.strip()
        if not seg_str:
            continue
        if seg_str.startswith("__CODE_BLOCK_") and seg_str.endswith("__"):
            code_text = code_blocks.get(seg_str, "").strip()
            if code_text:
                code_chunks = code_chunker.chunk(code_text)
                for ch in code_chunks:
                    if ch and ch.text.strip():
                        collected.append({"text": ch.text.strip(), "tokens": int(ch.token_count)})
            continue

        # Prose segment via sentence chunker
        prose_chunks = sent_chunker.chunk(seg_str)
        for ch in prose_chunks:
            if ch and ch.text.strip():
                collected.append({"text": ch.text.strip(), "tokens": int(ch.token_count)})

    # Merge small chunks (< min_chunk_tokens)
    merged: List[str] = []
    for item in collected:
        txt = item["text"]
        toks = int(item.get("tokens", 0))
        if toks < min_chunk_tokens and merged:
            merged[-1] = (merged[-1] + " " + txt).strip()
        else:
            merged.append(txt)

    merged = [c.strip() for c in merged if c and c.strip()]
    return merged


def _read_text_file(file_path: str) -> str:
    """Read text file with multiple encoding fallbacks"""
    encodings_to_try = ["utf-8", "utf-8-sig", "latin-1", "cp1252", "iso-8859-1"]

    for encoding in encodings_to_try:
        try:
            with open(file_path, encoding=encoding) as f:
                content = f.read()
            return content
        except UnicodeDecodeError:
            continue
        except Exception:
            continue

    try:
        with open(file_path, "rb") as f:
            binary_content = f.read()
        content = binary_content.decode("utf-8", errors="replace")
        return content
    except Exception:
        return ""


def _extract_text_from_pdf(file_path: str) -> str:
    """Extract text from PDF files"""
    try:
        import fitz

        pdf_document = fitz.open(file_path)
        content = ""
        for page_num in range(len(pdf_document)):
            page = pdf_document.load_page(page_num)
            content += page.get_text() + "\n"
        pdf_document.close()
        return content
    except ImportError:
        return ""
    except Exception:
        return ""


def _extract_text_from_docx(file_path: str) -> str:
    """Extract text from DOCX files"""
    try:
        from docx import Document

        doc = Document(file_path)
        content = "\n".join([paragraph.text for paragraph in doc.paragraphs if paragraph.text.strip()])
        return content
    except ImportError:
        return ""
    except Exception:
        return ""


async def process_file(
    file_path: str,
    collection_name: str = None,
    file_id: str = None,
    project_id: str | None = None,
    meeting_id: str | None = None,
    owner_user_id: str | None = None,
    file_type: str | None = None,
) -> bool:
    """Process a file and store it in Qdrant"""
    try:
        # Read file content
        if not os.path.exists(file_path):
            return False

        content = ""
        file_extension = os.path.splitext(file_path)[1].lower()
        mime_type, _ = mimetypes.guess_type(file_path)

        # Handle different file types
        if file_extension in [".pdf"] or (mime_type and "pdf" in mime_type):
            content = _extract_text_from_pdf(file_path)
        elif file_extension in [".docx"] or (mime_type and "wordprocessingml" in mime_type):
            content = _extract_text_from_docx(file_path)
        elif file_extension in [
            ".txt",
            ".md",
            ".json",
            ".xml",
            ".html",
            ".py",
            ".js",
            ".ts",
            ".css",
            ".csv",
        ] or (mime_type and ("text" in mime_type or "json" in mime_type or "xml" in mime_type)):
            content = _read_text_file(file_path)
        else:
            # Try to read as text anyway
            content = _read_text_file(file_path)

        if not content or not content.strip():
            return False

        # Default collection name from settings
        if not collection_name:
            collection_name = settings.QDRANT_COLLECTION_NAME

        # Generate embeddings for chunks
        from app.utils.llm import embed_documents

        # Simple chunking
        chunks = chunk_text(content)

        if not chunks:
            return False

        embeddings = await embed_documents(chunks)

        if not embeddings:
            return False

        # Ensure collection exists with correct vector size
        vector_dim = len(embeddings[0])
        await create_collection_if_not_exist(collection_name, vector_dim)

        # Prepare simple payloads
        payloads = []
        for i, chunk in enumerate(chunks):
            payload = {
                "text": chunk,
                "chunk_index": i,
                "source_file": os.path.basename(file_path),
                "total_chunks": len(chunks),
            }

            # Include file_id if provided (important for search filtering)
            if file_id:
                payload["file_id"] = file_id
            else:
                payload["file_id"] = "unknown"

            # Scope metadata for server-side filtering
            if project_id:
                payload["project_id"] = project_id
            if meeting_id:
                payload["meeting_id"] = meeting_id
            if owner_user_id:
                payload["uploaded_by"] = owner_user_id
            if file_type:
                payload["file_type"] = file_type
            payload["is_global"] = bool(not project_id and not meeting_id and owner_user_id)

            payloads.append(payload)

        # Store in Qdrant
        success = await upsert_vectors(collection_name, embeddings, payloads)

        return success

    except Exception as e:
        print(f"Error processing file {file_path}: {str(e)}")
        return False


async def delete_file_vectors(file_id: str, collection_name: str | None = None) -> bool:
    """Delete all vectors for a specific file_id from the collection"""
    client = get_qdrant_client()

    try:
        if not collection_name:
            collection_name = settings.QDRANT_COLLECTION_NAME
        filter_condition = qmodels.Filter(must=[qmodels.FieldCondition(key="file_id", match=qmodels.MatchValue(value=file_id))])

        client.delete(
            collection_name=collection_name,
            points_selector=qmodels.FilterSelector(filter=filter_condition),
        )

        return True

    except Exception:
        return False


async def delete_transcript_vectors(transcript_id: str, collection_name: str | None = None) -> bool:
    """Delete all vectors for a specific transcript_id from the collection"""
    client = get_qdrant_client()

    try:
        if not collection_name:
            collection_name = settings.QDRANT_COLLECTION_NAME
        filter_condition = qmodels.Filter(must=[qmodels.FieldCondition(key="transcript_id", match=qmodels.MatchValue(value=transcript_id))])

        client.delete(
            collection_name=collection_name,
            points_selector=qmodels.FilterSelector(filter=filter_condition),
        )

        return True

    except Exception:
        return False


async def update_file_vectors_metadata(
    file_id: str,
    project_id: str | None = None,
    meeting_id: str | None = None,
    owner_user_id: str | None = None,
    collection_name: str | None = None,
) -> bool:
    """Update vector payloads for a file with new project_id and/or meeting_id"""
    client = get_qdrant_client()

    try:
        if not collection_name:
            collection_name = settings.QDRANT_COLLECTION_NAME

        filter_condition = qmodels.Filter(must=[qmodels.FieldCondition(key="file_id", match=qmodels.MatchValue(value=file_id))])

        # Fetch all point IDs for this file
        points, _ = client.scroll(
            collection_name=collection_name,
            scroll_filter=filter_condition,
            limit=100,
        )

        if not points:
            return True

        point_ids = [point.id for point in points]

        payload = {
            "project_id": project_id,
            "meeting_id": meeting_id,
            "is_global": bool(not project_id and not meeting_id and owner_user_id),
        }

        client.set_payload(
            collection_name=collection_name,
            payload=payload,
            points=point_ids,
            wait=True,
        )

        return True

    except Exception:
        return False


async def reindex_file(
    file_path: str,
    file_id: str,
    collection_name: str | None = None,
    project_id: str | None = None,
    meeting_id: str | None = None,
    owner_user_id: str | None = None,
    file_type: str | None = None,
) -> bool:
    """Reindex a file by first deleting existing vectors, then indexing anew"""
    await delete_file_vectors(file_id, collection_name)
    return await process_file(
        file_path,
        collection_name,
        file_id,
        project_id=project_id,
        meeting_id=meeting_id,
        owner_user_id=owner_user_id,
        file_type=file_type,
    )


async def query_documents_by_meeting_id(
    meeting_id: str,
    collection_name: str | None = None,
    top_k: int = 10,
    db: Session | None = None,
    user_id: str | None = None,
) -> List[Dict[str, Any]]:
    """Query all documents for a specific meeting_id"""
    # Validate access if db and user_id provided
    if db and user_id:
        try:
            from uuid import UUID

            meeting = get_meeting(db, UUID(meeting_id), UUID(user_id))
            if not meeting:
                return []
        except Exception:
            return []

    if not collection_name:
        collection_name = settings.QDRANT_COLLECTION_NAME

    client = get_qdrant_client()

    try:
        all_points = []
        offset = None
        limit = 100

        while True:
            points, next_offset = client.scroll(collection_name=collection_name, limit=limit, offset=offset, with_payload=True, with_vectors=False)

            if not points:
                break

            for point in points:
                if point.payload and point.payload.get("meeting_id") == meeting_id:
                    all_points.append(point)

            offset = next_offset
            if not offset or len(all_points) >= top_k:
                break

        filtered_points = all_points[:top_k]

        documents = []
        for point in filtered_points:
            doc = {
                "id": point.id,
                "score": 1.0,
                "payload": point.payload or {},
                "vector": [],
            }
            documents.append(doc)

        return documents

    except Exception:
        return []


async def query_documents_by_project_id(
    project_id: str,
    collection_name: str | None = None,
    top_k: int = 10,
    db: Session | None = None,
    user_id: str | None = None,
) -> List[Dict[str, Any]]:
    """Query documents scoped to a specific project_id"""
    # Validate access if db and user_id provided
    if db and user_id:
        try:
            from uuid import UUID

            if not is_user_in_project(db, UUID(project_id), UUID(user_id)):
                return []
        except Exception:
            return []

    if not project_id:
        return []

    if not collection_name:
        collection_name = settings.QDRANT_COLLECTION_NAME

    client = get_qdrant_client()

    filter_condition = qmodels.Filter(must=[qmodels.FieldCondition(key="project_id", match=qmodels.MatchValue(value=project_id))])

    try:
        documents: List[dict] = []
        offset = None
        limit = min(max(top_k, 1), 100)

        while len(documents) < top_k:
            points, next_offset = client.scroll(
                collection_name=collection_name,
                limit=limit,
                offset=offset,
                with_payload=True,
                with_vectors=False,
                scroll_filter=filter_condition,
            )

            if not points:
                break

            for point in points:
                doc = {
                    "id": point.id,
                    "score": 1.0,
                    "payload": point.payload or {},
                    "vector": [],
                }
                documents.append(doc)
                if len(documents) >= top_k:
                    break

            offset = next_offset
            if not offset:
                break

        return documents

    except Exception:
        return []


async def query_documents_by_file_id(
    file_id: str,
    collection_name: str | None = None,
    top_k: int = 10,
    db: Session | None = None,
    user_id: str | None = None,
) -> List[Dict[str, Any]]:
    """Query documents scoped to a specific file_id"""
    # Validate access if db and user_id provided
    if db and user_id:
        try:
            from uuid import UUID

            file_obj = get_file(db, UUID(file_id))
            if not file_obj or not check_file_access(db, file_obj, UUID(user_id)):
                return []
        except Exception:
            return []

    if not file_id:
        return []

    if not collection_name:
        collection_name = settings.QDRANT_COLLECTION_NAME

    client = get_qdrant_client()

    filter_condition = qmodels.Filter(must=[qmodels.FieldCondition(key="file_id", match=qmodels.MatchValue(value=file_id))])

    try:
        documents: List[dict] = []
        offset = None
        limit = min(max(top_k, 1), 100)

        while len(documents) < top_k:
            points, next_offset = client.scroll(
                collection_name=collection_name,
                limit=limit,
                offset=offset,
                with_payload=True,
                with_vectors=False,
                scroll_filter=filter_condition,
            )

            if not points:
                break

            for point in points:
                doc = {
                    "id": point.id,
                    "score": 1.0,
                    "payload": point.payload or {},
                    "vector": [],
                }
                documents.append(doc)
                if len(documents) >= top_k:
                    break

            offset = next_offset
            if not offset:
                break

        return documents

    except Exception:
        return []
