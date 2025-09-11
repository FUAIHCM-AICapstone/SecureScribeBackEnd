import logging
import mimetypes
import os
import uuid
from typing import Any, Dict, List

from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels

from app.core.config import settings

logger = logging.getLogger(__name__)


class QdrantService:
    def __init__(self):
        self.client = None
        self._initialize_client()
        self.ai_service = None  # Will be injected for embedding operations
        print("🟢 \033[92mQdrantService initialized\033[0m")

    def _initialize_client(self):
        """Initialize Qdrant client"""
        self.client = QdrantClient(
            host=settings.QDRANT_HOST,
            port=settings.QDRANT_PORT,
            timeout=30.0
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
                print(f"🟡 \033[93mCollection '{collection_name}' already exists\033[0m")
                return False

            self.client.create_collection(
                collection_name=collection_name,
                vectors_config=qmodels.VectorParams(
                    size=dim, distance=qmodels.Distance.COSINE
                ),
            )
            print(f"🟢 \033[92mCreated collection '{collection_name}' with dimension {dim}\033[0m")
            return True

        except Exception as e:
            print(f"🔴 \033[91mFailed to create collection '{collection_name}': {e}\033[0m")
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

    def set_ai_service(self, ai_service):
        """Set the AI service for embedding operations"""
        self.ai_service = ai_service
        print("🟢 \033[92mAI service set for QdrantService\033[0m")

    def chunk_text(self, text: str, chunk_size: int = 1000) -> List[str]:
        """Simple text chunking"""
        if not text:
            return []

        chunks = []
        for i in range(0, len(text), chunk_size):
            chunk = text[i:i + chunk_size].strip()
            if chunk:
                chunks.append(chunk)

        print(f"🟢 \033[92mCreated {len(chunks)} text chunks\033[0m")
        return chunks

    def _read_text_file(self, file_path: str) -> str:
        """Read text file with multiple encoding fallbacks"""
        encodings_to_try = ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252', 'iso-8859-1']

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

        # If all encodings fail, try binary mode and decode what we can
        try:
            with open(file_path, 'rb') as f:
                binary_content = f.read()
            # Try to decode as much as possible
            content = binary_content.decode('utf-8', errors='replace')
            print("🟡 \033[93mRead file as binary, some characters may be replaced\033[0m")
            return content
        except Exception as e:
            print(f"🔴 \033[91mFailed to read file even in binary mode: {e}\033[0m")
            return ""

    def _extract_text_from_pdf(self, file_path: str) -> str:
        """Extract text from PDF files"""
        try:
            import fitz  # PyMuPDF - import here to handle optional dependency
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

    def _extract_text_from_docx(self, file_path: str) -> str:
        """Extract text from DOCX files"""
        try:
            from docx import Document  # python-docx - import here to handle optional dependency
            doc = Document(file_path)
            content = "\n".join([paragraph.text for paragraph in doc.paragraphs if paragraph.text.strip()])
            print(f"🟢 \033[92mExtracted text from DOCX: {len(content)} characters\033[0m")
            return content
        except ImportError:
            print("🔴 \033[91mpython-docx not installed - cannot process DOCX files\033[0m")
            return ""
        except Exception as e:
            print(f"🔴 \033[91mFailed to extract text from DOCX: {e}\033[0m")
            return ""

    async def process_file(
        self, file_path: str, collection_name: str = "documents", file_id: str = None
    ) -> bool:
        """Process a file and store it in Qdrant"""
        if not self.ai_service:
            print("🔴 \033[91mAI service not set\033[0m")
            return False

        try:
            # Read file content
            if not os.path.exists(file_path):
                print(f"🔴 \033[91mFile not found: {file_path}\033[0m")
                return False

            content = ""
            file_extension = os.path.splitext(file_path)[1].lower()
            mime_type, _ = mimetypes.guess_type(file_path)

            print(f"🟢 \033[92mProcessing file: {os.path.basename(file_path)} ({file_extension}, {mime_type})\033[0m")

            # Handle different file types
            if file_extension in ['.pdf'] or (mime_type and 'pdf' in mime_type):
                content = self._extract_text_from_pdf(file_path)
            elif file_extension in ['.docx'] or (mime_type and 'wordprocessingml' in mime_type):
                content = self._extract_text_from_docx(file_path)
            elif file_extension in ['.txt', '.md', '.json', '.xml', '.html', '.py', '.js', '.ts', '.css', '.csv'] or \
                 (mime_type and ('text' in mime_type or 'json' in mime_type or 'xml' in mime_type)):
                content = self._read_text_file(file_path)
            else:
                # Try to read as text anyway
                content = self._read_text_file(file_path)

            if not content or not content.strip():
                print(f"🟡 \033[93mNo readable content found in: {os.path.basename(file_path)}\033[0m")
                return False

            print(f"🟢 \033[92mExtracted {len(content)} characters from {os.path.basename(file_path)}\033[0m")

            # Create collection if needed
            embed_dim = getattr(self.ai_service, "embed_dim", 768)
            await self.create_collection_if_not_exist(collection_name, embed_dim)

            # Simple chunking
            chunks = self.chunk_text(content)

            if not chunks:
                print("🔴 \033[91mNo chunks generated\033[0m")
                return False

            # Generate embeddings
            embeddings = await self.ai_service.embed_documents(chunks)

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
                    print(f"🟢 \033[92mIncluding file_id {file_id} in payload for chunk {i}\033[0m")
                else:
                    print(f"🟡 \033[93mWarning: No file_id provided for chunk {i}\033[0m")

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
        if not self.ai_service:
            print("🔴 \033[91mAI service not set\033[0m")
            return []

        try:
            # Generate query embedding
            query_embedding = await self.ai_service.embed_query(query)

            # Search in Qdrant
            results = await self.search_vectors(collection_name, query_embedding, top_k)

            # Format results
            formatted_results = []
            for i, result in enumerate(results):
                payload = getattr(result, "payload", {}) or {}
                score = getattr(result, "score", 0.0)

                formatted_results.append({
                    "rank": i + 1,
                    "score": score,
                    "text": payload.get("text", ""),
                    "source_file": payload.get("source_file", ""),
                    "chunk_index": payload.get("chunk_index", 0),
                })

            print(f"🟢 \033[92mFound {len(formatted_results)} results for query\033[0m")
            return formatted_results

        except Exception as e:
            print(f"🔴 \033[91mSearch failed: {e}\033[0m")
            return []

    async def delete_file_vectors(self, file_id: str, collection_name: str = "documents") -> bool:
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
                        key="file_id",
                        match=qmodels.MatchValue(value=file_id)
                    )
                ]
            )

            # Delete points matching the filter
            self.client.delete(
                collection_name=collection_name,
                points_selector=qmodels.FilterSelector(filter=filter_condition)
            )

            print(f"🟢 \033[92mDeleted existing vectors for file_id {file_id}\033[0m")
            return True

        except Exception as e:
            print(f"🔴 \033[91mFailed to delete vectors for file_id {file_id}: {e}\033[0m")
            return False

    async def reindex_file(self, file_path: str, file_id: str, collection_name: str = "documents") -> bool:
        """Reindex a file by first deleting existing vectors, then indexing anew"""
        print(f"🔄 \033[94mReindexing file {file_id}\033[0m")

        # First, delete existing vectors for this file
        await self.delete_file_vectors(file_id, collection_name)

        # Then, process the file with the file_id
        return await self.process_file(file_path, collection_name, file_id)


qdrant_service = QdrantService()
