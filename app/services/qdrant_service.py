import mimetypes
import os
import re
import uuid
from typing import Any, Dict, List

import tiktoken
from qdrant_client.http import models as qmodels

from app.core.config import settings
from app.utils.qdrant import get_qdrant_client


async def create_collection_if_not_exist(collection_name: str, dim: int) -> bool:
    """Create a collection if it doesn't exist"""
    client = get_qdrant_client()

    try:
        existing_collections = [c.name for c in client.get_collections().collections]
        if collection_name in existing_collections:
            print(f"🟡 \033[93mCollection '{collection_name}' already exists\033[0m")
            return False

        client.create_collection(
            collection_name=collection_name,
            vectors_config=qmodels.VectorParams(
                size=dim, distance=qmodels.Distance.COSINE
            ),
        )
        print(
            f"🟢 \033[92mCreated collection '{collection_name}' with dimension {dim}\033[0m"
        )
        return True

    except Exception as e:
        print(f"🔴 \033[91mFailed to create collection '{collection_name}': {e}\033[0m")
        return False


async def upsert_vectors(
    collection: str, vectors: List[List[float]], payloads: List[Dict[str, Any]]
) -> bool:
    """Upsert vectors to a collection"""
    if not vectors:
        return False

    client = get_qdrant_client()
    try:
        points = []
        for idx, vec in enumerate(vectors):
            point_id = str(uuid.uuid4())
            payload = payloads[idx] if idx < len(payloads) else {}
            points.append(qmodels.PointStruct(id=point_id, vector=vec, payload=payload))

        client.upsert(collection_name=collection, points=points)
        print(f"🟢 \033[92mUpserted {len(points)} vectors to '{collection}'\033[0m")
        return True

    except Exception as e:
        print(f"🔴 \033[91mFailed to upsert vectors: {e}\033[0m")
        return False


async def search_vectors(
    collection: str,
    query_vector: List[float],
    top_k: int = 5,
    query_filter: qmodels.Filter | None = None,
) -> List[Any]:
    """Search for similar vectors in a collection"""
    if not query_vector:
        return []

    client = get_qdrant_client()
    try:
        results = client.search(
            collection_name=collection,
            query_vector=query_vector,
            limit=min(max(top_k, 1), 100),
            query_filter=query_filter,
        )
        print(f"🟢 \033[92mFound {len(results)} results in '{collection}'\033[0m")
        return results

    except Exception as e:
        print(f"🔴 \033[91mSearch failed: {e}\033[0m")
        return []


def chunk_text(text: str, chunk_size: int = 1000) -> List[str]:
    """Token-aware, sentence-boundary chunking with overlap and code-block preservation."""
    if not text:
        return []

    from collections import Counter

    enc = tiktoken.get_encoding("cl100k_base")

    # params
    overlap_ratio = 0.15
    min_chunk_tokens = 200

    # Normalize whitespace
    text = text.replace("\r\n", "\n").replace("\r", "\n").strip()

    # Simple boilerplate removal
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    line_counts = Counter(lines)
    boilerplate = {ln for ln, cnt in line_counts.items() if cnt > 2 and len(ln) < 200}
    if boilerplate:
        text_lines = [ln for ln in text.splitlines() if ln.strip() not in boilerplate]
        text = "\n".join(text_lines).strip()

    text = re.sub(r"[ \t]+", " ", text)

    # Extract code blocks
    code_blocks = {}

    def _code_repl(m):
        idx = len(code_blocks)
        key = f"__CODE_BLOCK_{idx}__"
        code_blocks[key] = m.group(0)
        return f"\n{key}\n"

    text_no_code = re.sub(r"```.*?```", _code_repl, text, flags=re.DOTALL)

    # Split into sentences (avoid variable-width lookbehind)
    rough_sentences = re.split(r"(?<=[\.!?])\s+|\n+", text_no_code)
    sentences = [s.strip() for s in rough_sentences if s and s.strip()]

    chunks: List[str] = []
    current_chunk_sents: List[str] = []
    current_chunk_tokens = 0

    def _finalize_current_chunk():
        nonlocal current_chunk_sents, current_chunk_tokens
        if not current_chunk_sents:
            return
        chunk_text = " ".join(current_chunk_sents).strip()
        try:
            token_count = len(enc.encode(chunk_text))
        except Exception:
            token_count = sum(len(enc.encode(s)) for s in current_chunk_sents)
        if token_count < min_chunk_tokens and chunks:
            chunks[-1] = (chunks[-1] + " " + chunk_text).strip()
        else:
            chunks.append(chunk_text)
        current_chunk_sents = []
        current_chunk_tokens = 0

    for sent in sentences:
        if sent.startswith("__CODE_BLOCK_") and sent.endswith("__"):
            _finalize_current_chunk()
            code_text = code_blocks.get(sent, sent)
            chunks.append(code_text.strip())
            continue

        try:
            sent_tokens = len(enc.encode(sent))
        except Exception:
            sent_tokens = max(1, len(sent.split()))

        if current_chunk_tokens + sent_tokens > chunk_size:
            _finalize_current_chunk()

            overlap_tokens = int(chunk_size * overlap_ratio)
            if overlap_tokens > 0 and chunks:
                last_chunk = chunks[-1]
                try:
                    last_tokens = enc.encode(last_chunk)
                    if len(last_tokens) > overlap_tokens:
                        tail_tokens = last_tokens[-overlap_tokens:]
                    else:
                        tail_tokens = last_tokens
                    overlap_text = enc.decode(tail_tokens).strip()
                except Exception:
                    overlap_text = ""
                if overlap_text:
                    current_chunk_sents = [overlap_text]
                    try:
                        current_chunk_tokens = len(enc.encode(overlap_text))
                    except Exception:
                        current_chunk_tokens = max(1, len(overlap_text.split()))
                else:
                    current_chunk_sents = []
                    current_chunk_tokens = 0
            else:
                current_chunk_sents = []
                current_chunk_tokens = 0

        current_chunk_sents.append(sent)
        current_chunk_tokens += sent_tokens

        if current_chunk_tokens >= chunk_size and len(current_chunk_sents) == 1:
            _finalize_current_chunk()

    _finalize_current_chunk()

    # Replace placeholders
    if code_blocks:
        for i, ch in enumerate(chunks):
            for key, code in code_blocks.items():
                if key in ch:
                    chunks[i] = chunks[i].replace(key, code)

    chunks = [c.strip() for c in chunks if c and c.strip()]
    print(f"🟢 \033[92mCreated {len(chunks)} text chunks\033[0m")
    return chunks


def _read_text_file(file_path: str) -> str:
    """Read text file with multiple encoding fallbacks"""
    encodings_to_try = ["utf-8", "utf-8-sig", "latin-1", "cp1252", "iso-8859-1"]

    for encoding in encodings_to_try:
        try:
            with open(file_path, encoding=encoding) as f:
                content = f.read()
            print(f"🟢 \033[92mSuccessfully read file with {encoding} encoding\033[0m")
            return content
        except UnicodeDecodeError:
            continue
        except Exception as e:
            print(f"🔴 \033[91mError reading with {encoding}: {e}\033[0m")
            continue

    try:
        with open(file_path, "rb") as f:
            binary_content = f.read()
        content = binary_content.decode("utf-8", errors="replace")
        print("🟡 \033[93mRead file as binary, some characters may be replaced\033[0m")
        return content
    except Exception as e:
        print(f"🔴 \033[91mFailed to read file even in binary mode: {e}\033[0m")
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
        print(f"🟢 \033[92mExtracted text from PDF: {len(content)} characters\033[0m")
        return content
    except ImportError:
        print("🔴 \033[91mPyMuPDF not installed - cannot process PDF files\033[0m")
        return ""
    except Exception as e:
        print(f"🔴 \033[91mFailed to extract text from PDF: {e}\033[0m")
        return ""


def _extract_text_from_docx(file_path: str) -> str:
    """Extract text from DOCX files"""
    try:
        from docx import Document

        doc = Document(file_path)
        content = "\n".join(
            [paragraph.text for paragraph in doc.paragraphs if paragraph.text.strip()]
        )
        print(f"🟢 \033[92mExtracted text from DOCX: {len(content)} characters\033[0m")
        return content
    except ImportError:
        print("🔴 \033[91mpython-docx not installed - cannot process DOCX files\033[0m")
        return ""
    except Exception as e:
        print(f"🔴 \033[91mFailed to extract text from DOCX: {e}\033[0m")
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
            print(f"🔴 \033[91mFile not found: {file_path}\033[0m")
            return False

        content = ""
        file_extension = os.path.splitext(file_path)[1].lower()
        mime_type, _ = mimetypes.guess_type(file_path)

        print(
            f"🟢 \033[92mProcessing file: {os.path.basename(file_path)} ({file_extension}, {mime_type})\033[0m"
        )

        # Handle different file types
        if file_extension in [".pdf"] or (mime_type and "pdf" in mime_type):
            content = _extract_text_from_pdf(file_path)
        elif file_extension in [".docx"] or (
            mime_type and "wordprocessingml" in mime_type
        ):
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
        ] or (
            mime_type
            and ("text" in mime_type or "json" in mime_type or "xml" in mime_type)
        ):
            content = _read_text_file(file_path)
        else:
            # Try to read as text anyway
            content = _read_text_file(file_path)

        if not content or not content.strip():
            print(
                f"🟡 \033[93mNo readable content found in: {os.path.basename(file_path)}\033[0m"
            )
            return False

        print(
            f"🟢 \033[92mExtracted {len(content)} characters from {os.path.basename(file_path)}\033[0m"
        )

        # Default collection name from settings
        if not collection_name:
            collection_name = settings.QDRANT_COLLECTION_NAME

        # Create collection if needed
        from app.utils.llm import embed_documents

        await create_collection_if_not_exist(collection_name, 3072)

        # Simple chunking
        chunks = chunk_text(content)

        if not chunks:
            print("🔴 \033[91mNo chunks generated\033[0m")
            return False

        # Generate embeddings
        embeddings = await embed_documents(chunks)

        if not embeddings:
            print("🔴 \033[91mEmbedding generation failed\033[0m")
            return False

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
                print(
                    f"🟢 \033[92mIncluding file_id {file_id} in payload for chunk {i}\033[0m"
                )
            else:
                print(f"🟡 \033[93mWarning: No file_id provided for chunk {i}\033[0m")

            # Scope metadata for server-side filtering
            if project_id:
                payload["project_id"] = project_id
            if meeting_id:
                payload["meeting_id"] = meeting_id
            if owner_user_id:
                payload["uploaded_by"] = owner_user_id
            if file_type:
                payload["file_type"] = file_type
            payload["is_global"] = bool(
                not project_id and not meeting_id and owner_user_id
            )

            payloads.append(payload)

        # Store in Qdrant
        success = await upsert_vectors(collection_name, embeddings, payloads)

        if success:
            print(f"🟢 \033[92mSuccessfully processed {len(chunks)} chunks\033[0m")
        else:
            print("🔴 \033[91mFailed to store chunks\033[0m")

        return success

    except Exception as e:
        print(f"🔴 \033[91mProcessing failed: {e}\033[0m")
        return False



async def delete_file_vectors(file_id: str, collection_name: str | None = None) -> bool:
    """Delete all vectors for a specific file_id from the collection"""
    client = get_qdrant_client()

    try:
        if not collection_name:
            collection_name = settings.QDRANT_COLLECTION_NAME
        filter_condition = qmodels.Filter(
            must=[
                qmodels.FieldCondition(
                    key="file_id", match=qmodels.MatchValue(value=file_id)
                )
            ]
        )

        client.delete(
            collection_name=collection_name,
            points_selector=qmodels.FilterSelector(filter=filter_condition),
        )

        print(f"🟢 \033[92mDeleted existing vectors for file_id {file_id}\033[0m")
        return True

    except Exception as e:
        print(f"🔴 \033[91mFailed to delete vectors for file_id {file_id}: {e}\033[0m")
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
    print(f"🔄 \033[94mReindexing file {file_id}\033[0m")
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
