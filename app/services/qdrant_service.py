import logging
import mimetypes
import os
import re
import uuid
from typing import Any, Dict, List

import tiktoken
from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels

from app.core.config import settings

logger = logging.getLogger(__name__)


class QdrantService:
    def __init__(self):
        self.client = None
        self._initialize_client()
        print("🟢 \033[92mQdrantService initialized\033[0m")

    def _initialize_client(self):
        """Initialize Qdrant client"""
        self.client = QdrantClient(
            host=settings.QDRANT_HOST, port=settings.QDRANT_PORT, timeout=30.0
        )
        print("🟢 \033[92mQdrant client connected\033[0m")

    async def create_collection_if_not_exist(
        self, collection_name: str, dim: int
    ) -> bool:
        """Create a collection if it doesn't exist"""
        if not self.client:
            print("🔴 \033[91mQdrant client not initialized\033[0m")
            return False

        try:
            existing_collections = [
                c.name for c in self.client.get_collections().collections
            ]
            if collection_name in existing_collections:
                print(
                    f"🟡 \033[93mCollection '{collection_name}' already exists\033[0m"
                )
                return False

            self.client.create_collection(
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
            print(
                f"🔴 \033[91mFailed to create collection '{collection_name}': {e}\033[0m"
            )
            return False

    async def upsert_vectors(
        self,
        collection: str,
        vectors: List[List[float]],
        payloads: List[Dict[str, Any]],
    ) -> bool:
        """Upsert vectors to a collection"""
        if not self.client or not vectors:
            return False

        try:
            points = []
            for idx, vec in enumerate(vectors):
                point_id = str(uuid.uuid4())
                payload = payloads[idx] if idx < len(payloads) else {}
                points.append(
                    qmodels.PointStruct(id=point_id, vector=vec, payload=payload)
                )

            self.client.upsert(collection_name=collection, points=points)
            print(f"🟢 \033[92mUpserted {len(points)} vectors to '{collection}'\033[0m")
            return True

        except Exception as e:
            print(f"🔴 \033[91mFailed to upsert vectors: {e}\033[0m")
            return False

    async def search_vectors(
        self, collection: str, query_vector: List[float], top_k: int = 5
    ) -> List[Any]:
        """Search for similar vectors in a collection"""
        if not self.client or not query_vector:
            return []

        try:
            results = self.client.search(
                collection_name=collection,
                query_vector=query_vector,
                limit=min(max(top_k, 1), 100),
            )
            print(f"🟢 \033[92mFound {len(results)} results in '{collection}'\033[0m")
            return results

        except Exception as e:
            print(f"🔴 \033[91mSearch failed: {e}\033[0m")
            return []

    def chunk_text(self, text: str, chunk_size: int = 1000) -> List[str]:
        """Token-aware, sentence-boundary chunking with overlap and code-block preservation.
        - chunk_size: number of tokens (tiktoken)
        - internal overlap_ratio (≈15%), min_chunk_tokens (≈200)
        Returns List[str] (no metadata) as bạn yêu cầu.
        """
        if not text:
            return []

        from collections import Counter

        try:
            import tiktoken
        except Exception as e:
            raise RuntimeError(
                "tiktoken is required for token-aware chunking. Install it: pip install tiktoken"
            ) from e

        # params (tweak here if needed)
        overlap_ratio = 0.15
        min_chunk_tokens = 200
        enc = tiktoken.get_encoding("cl100k_base")

        # Normalize whitespace (preserve line breaks for boilerplate detection)
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        # Trim long leading/trailing whitespace
        text = text.strip()

        # --- Simple boilerplate/header-footer removal ---
        # Find repeated short lines (likely headers/footers) and remove them
        lines = [ln.strip() for ln in text.splitlines() if ln.strip() != ""]
        line_counts = Counter(lines)
        boilerplate = {
            ln for ln, cnt in line_counts.items() if cnt > 2 and len(ln) < 200
        }
        if boilerplate:
            # remove exact matches of those lines
            text_lines = [
                ln for ln in text.splitlines() if ln.strip() not in boilerplate
            ]
            text = "\n".join(text_lines).strip()

        # Collapse multiple spaces but keep single newlines as separators for sentence splitting convenience
        # (We will split by sentence punctuation and newlines later)
        text = re.sub(r"[ \t]+", " ", text)

        # --- Extract fenced code blocks (```...```) and replace with placeholders ---
        code_blocks = {}

        def _code_repl(m):
            idx = len(code_blocks)
            key = f"__CODE_BLOCK_{idx}__"
            code_blocks[key] = m.group(0)
            # ensure placeholder sits on its own line so sentence-splitting keeps it separate
            return f"\n{key}\n"

        text_no_code = re.sub(r"```.*?```", _code_repl, text, flags=re.DOTALL)

        # --- Split into sentences (approx) preserving placeholders as separate elements ---
        # split on sentence enders or blank lines; keep placeholders as standalone items
        # pattern splits on punctuation followed by whitespace OR on one+ newlines
        rough_sentences = re.split(r'(?<=[\.\?\!]["\']?)\s+|\n+', text_no_code)
        # Filter empty strings, preserve order
        sentences = [s.strip() for s in rough_sentences if s and s.strip()]

        chunks: List[str] = []
        current_chunk_sents: List[str] = []
        current_chunk_tokens = 0

        def _finalize_current_chunk():
            nonlocal current_chunk_sents, current_chunk_tokens
            if not current_chunk_sents:
                return
            chunk_text = " ".join(current_chunk_sents).strip()
            # merge small chunks into previous one when possible
            try:
                token_count = len(enc.encode(chunk_text))
            except Exception:
                token_count = sum(len(enc.encode(s)) for s in current_chunk_sents)
            if token_count < min_chunk_tokens and chunks:
                # merge into previous chunk
                chunks[-1] = (chunks[-1] + " " + chunk_text).strip()
            else:
                chunks.append(chunk_text)
            current_chunk_sents = []
            current_chunk_tokens = 0

        for sent in sentences:
            # If sentence is a code placeholder, emit current chunk first, then the code block as its own chunk.
            if sent.startswith("__CODE_BLOCK_") and sent.endswith("__"):
                # finalize what's accumulated
                _finalize_current_chunk()
                code_text = code_blocks.get(sent, sent)
                # Keep code block intact as a separate chunk (even if large). Trim edges.
                chunks.append(code_text.strip())
                continue

            # token count for this sentence
            try:
                sent_tokens = len(enc.encode(sent))
            except Exception:
                # fallback: approximate by splitting words
                sent_tokens = max(1, len(sent.split()))

            # if adding this sentence would exceed chunk_size, finalize current chunk first
            if current_chunk_tokens + sent_tokens > chunk_size:
                # finalize
                _finalize_current_chunk()

                # implement overlap by taking last overlap_tokens from the previous chunk if possible
                overlap_tokens = int(chunk_size * overlap_ratio)
                if overlap_tokens > 0 and chunks:
                    # get last chunk tokens and take last overlap_tokens, decode back to text as seed
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
                        # Start the new chunk with the overlap text (so context preserved)
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

            # add current sentence to chunk
            current_chunk_sents.append(sent)
            current_chunk_tokens += sent_tokens

            # If a single sentence itself is larger than chunk_size (rare), flush it as its own chunk
            if current_chunk_tokens >= chunk_size and len(current_chunk_sents) == 1:
                _finalize_current_chunk()

        # finalize remaining
        _finalize_current_chunk()

        # Replace any leftover placeholders inside chunks with original code blocks (if any)
        if code_blocks:
            for i, ch in enumerate(chunks):
                for key, code in code_blocks.items():
                    if key in ch:
                        chunks[i] = chunks[i].replace(key, code)

        # Final trimming + remove empty
        chunks = [c.strip() for c in chunks if c and c.strip()]

        print(f"🟢 \033[92mCreated {len(chunks)} text chunks\033[0m")
        return chunks

    def _read_text_file(self, file_path: str) -> str:
        """Read text file with multiple encoding fallbacks"""
        encodings_to_try = ["utf-8", "utf-8-sig", "latin-1", "cp1252", "iso-8859-1"]

        for encoding in encodings_to_try:
            try:
                with open(file_path, encoding=encoding) as f:
                    content = f.read()
                print(
                    f"🟢 \033[92mSuccessfully read file with {encoding} encoding\033[0m"
                )
                return content
            except UnicodeDecodeError:
                continue
            except Exception as e:
                print(f"🔴 \033[91mError reading with {encoding}: {e}\033[0m")
                continue

        # If all encodings fail, try binary mode and decode what we can
        try:
            with open(file_path, "rb") as f:
                binary_content = f.read()
            # Try to decode as much as possible
            content = binary_content.decode("utf-8", errors="replace")
            print(
                "🟡 \033[93mRead file as binary, some characters may be replaced\033[0m"
            )
            return content
        except Exception as e:
            print(f"🔴 \033[91mFailed to read file even in binary mode: {e}\033[0m")
            return ""

    def _extract_text_from_pdf(self, file_path: str) -> str:
        """Extract text from PDF files"""
        try:
            import fitz  # type: ignore

            pdf_document = fitz.open(file_path)
            content = ""
            for page_num in range(len(pdf_document)):
                page = pdf_document.load_page(page_num)
                content += page.get_text() + "\n"
            pdf_document.close()
            print(
                f"🟢 \033[92mExtracted text from PDF: {len(content)} characters\033[0m"
            )
            return content
        except ImportError:
            print("🔴 \033[91mPyMuPDF not installed - cannot process PDF files\033[0m")
            return ""
        except Exception as e:
            print(f"🔴 \033[91mFailed to extract text from PDF: {e}\033[0m")
            return ""

    def _extract_text_from_docx(self, file_path: str) -> str:
        """Extract text from DOCX files"""
        try:
            from docx import Document  # type: ignore

            doc = Document(file_path)
            content = "\n".join(
                [
                    paragraph.text
                    for paragraph in doc.paragraphs
                    if paragraph.text.strip()
                ]
            )
            print(
                f"🟢 \033[92mExtracted text from DOCX: {len(content)} characters\033[0m"
            )
            return content
        except ImportError:
            print(
                "🔴 \033[91mpython-docx not installed - cannot process DOCX files\033[0m"
            )
            return ""
        except Exception as e:
            print(f"🔴 \033[91mFailed to extract text from DOCX: {e}\033[0m")
            return ""

    async def process_file(
        self, file_path: str, collection_name: str = "documents", file_id: str = None
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
                content = self._extract_text_from_pdf(file_path)
            elif file_extension in [".docx"] or (
                mime_type and "wordprocessingml" in mime_type
            ):
                content = self._extract_text_from_docx(file_path)
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
                content = self._read_text_file(file_path)
            else:
                # Try to read as text anyway
                content = self._read_text_file(file_path)

            if not content or not content.strip():
                print(
                    f"🟡 \033[93mNo readable content found in: {os.path.basename(file_path)}\033[0m"
                )
                return False

            print(
                f"🟢 \033[92mExtracted {len(content)} characters from {os.path.basename(file_path)}\033[0m"
            )

            # Create collection if needed
            from app.utils.llm import embed_documents

            await self.create_collection_if_not_exist(collection_name, 768)

            # Simple chunking
            chunks = self.chunk_text(content)

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
                    print(
                        f"🟡 \033[93mWarning: No file_id provided for chunk {i}\033[0m"
                    )

                payloads.append(payload)

            # Store in Qdrant
            success = await self.upsert_vectors(collection_name, embeddings, payloads)

            if success:
                print(f"🟢 \033[92mSuccessfully processed {len(chunks)} chunks\033[0m")
            else:
                print("🔴 \033[91mFailed to store chunks\033[0m")

            return success

        except Exception as e:
            print(f"🔴 \033[91mProcessing failed: {e}\033[0m")
            return False

    async def search_documents(
        self, query: str, collection_name: str = "documents", top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """Search documents in a collection"""
        try:
            # Generate query embedding
            from app.utils.llm import embed_query

            query_embedding = await embed_query(query)

            # Search in Qdrant
            results = await self.search_vectors(collection_name, query_embedding, top_k)

            # Format results
            formatted_results = []
            for i, result in enumerate(results):
                payload = getattr(result, "payload", {}) or {}
                score = getattr(result, "score", 0.0)

                formatted_results.append(
                    {
                        "rank": i + 1,
                        "score": score,
                        "text": payload.get("text", ""),
                        "source_file": payload.get("source_file", ""),
                        "chunk_index": payload.get("chunk_index", 0),
                    }
                )

            print(f"🟢 \033[92mFound {len(formatted_results)} results for query\033[0m")
            return formatted_results

        except Exception as e:
            print(f"🔴 \033[91mSearch failed: {e}\033[0m")
            return []

    async def delete_file_vectors(
        self, file_id: str, collection_name: str = "documents"
    ) -> bool:
        """Delete all vectors for a specific file_id from the collection"""
        if not self.client:
            print("🔴 \033[91mQdrant client not initialized\033[0m")
            return False

        try:
            # Create a filter to find vectors with the specific file_id
            from qdrant_client.http import models as qmodels

            filter_condition = qmodels.Filter(
                must=[
                    qmodels.FieldCondition(
                        key="file_id", match=qmodels.MatchValue(value=file_id)
                    )
                ]
            )

            # Delete points matching the filter
            self.client.delete(
                collection_name=collection_name,
                points_selector=qmodels.FilterSelector(filter=filter_condition),
            )

            print(f"🟢 \033[92mDeleted existing vectors for file_id {file_id}\033[0m")
            return True

        except Exception as e:
            print(
                f"🔴 \033[91mFailed to delete vectors for file_id {file_id}: {e}\033[0m"
            )
            return False

    async def reindex_file(
        self, file_path: str, file_id: str, collection_name: str = "documents"
    ) -> bool:
        """Reindex a file by first deleting existing vectors, then indexing anew"""
        print(f"🔄 \033[94mReindexing file {file_id}\033[0m")

        # First, delete existing vectors for this file
        await self.delete_file_vectors(file_id, collection_name)

        # Then, process the file with the file_id
        return await self.process_file(file_path, collection_name, file_id)


qdrant_service = QdrantService()
