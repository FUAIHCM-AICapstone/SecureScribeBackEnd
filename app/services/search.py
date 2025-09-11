import logging
from typing import Any, Dict, List

import google.generativeai as genai
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from app.core.config import settings

logger = logging.getLogger(__name__)


class AIService:
    def __init__(self):
        self.embed_dim = 768
        genai.configure(api_key=settings.GOOGLE_API_KEY)
        self.client = genai
        self.chat_client = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            api_key=settings.GOOGLE_API_KEY,
            temperature=0.7,
        )
        from app.services.qdrant_service import qdrant_service

        if not qdrant_service.ai_service:
            qdrant_service.set_ai_service(self)
        print("🟢 \033[92mAIService initialized\033[0m")

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

    async def embed_documents(self, docs: List[str]) -> List[List[float]]:
        """Generate embeddings for documents"""
        if not docs:
            return []

        try:
            embeddings = []
            for doc in docs:
                result = self.client.embed_content(
                    model="models/text-embedding-004",
                    content=doc,
                    task_type="retrieval_document",
                )
                if result and "embedding" in result:
                    embeddings.append(result["embedding"])

            if embeddings and embeddings[0]:
                self.embed_dim = len(embeddings[0])

            print(f"🟢 \033[92mGenerated {len(embeddings)} embeddings\033[0m")
            return embeddings

        except Exception as e:
            print(f"🔴 \033[91mEmbedding failed: {e}\033[0m")
            return []

    async def embed_query(self, query: str) -> List[float]:
        """Generate embedding for query"""
        try:
            result = self.client.embed_content(
                model="models/text-embedding-004",
                content=query,
                task_type="retrieval_query",
            )
            if result and "embedding" in result:
                return result["embedding"]
        except Exception as e:
            print(f"🔴 \033[91mQuery embedding failed: {e}\033[0m")

        return []

    async def chat_with_context(self, query: str, context: List[str] = None) -> str:
        """Simple RAG chat with document context"""
        try:
            # Build context from documents
            context_text = ""
            if context:
                context_text = "\n\n".join(context[:3])  # Limit to top 3 documents

            # Create messages
            system_message = SystemMessage(content="""
You are a helpful AI assistant. Use the provided context to answer questions accurately.
If the context doesn't have relevant information, provide a helpful general response.
Be conversational and provide comprehensive but concise responses.
""")

            user_content = f"Context:\n{context_text}\n\nQuestion: {query}" if context_text else f"Question: {query}"
            user_message = HumanMessage(content=user_content)

            # Generate response
            response = self.chat_client.invoke([system_message, user_message])

            print("🟢 \033[92mGenerated response for query\033[0m")
            return response.content

        except Exception as e:
            print(f"🔴 \033[91mChat failed: {e}\033[0m")
            return f"I encountered an error: {str(e)}"

    async def search_and_chat(self, query: str) -> str:
        """Search documents and generate response"""
        try:
            from app.services.qdrant_service import qdrant_service

            # Get query embedding
            query_vector = await self.embed_query(query)
            if not query_vector:
                return "Could not generate embedding for query"

            # Search for relevant documents
            results = await qdrant_service.search_vectors("documents", query_vector, top_k=5)

            # Extract text from results
            context_docs = []
            for result in results:
                payload = getattr(result, "payload", {}) or {}
                if isinstance(payload, dict):
                    text = payload.get("text", "")
                    if text:
                        context_docs.append(text)

            # Generate response with context
            response = await self.chat_with_context(query, context_docs)

            print(f"🟢 \033[92mFound {len(context_docs)} relevant documents\033[0m")
            return response

        except Exception as e:
            print(f"🔴 \033[91mSearch and chat failed: {e}\033[0m")
            return f"I encountered an error: {str(e)}"

    def get_status(self) -> Dict[str, Any]:
        """Get service status"""
        return {
            "embed_dim": self.embed_dim,
            "client_ready": self.client is not None,
            "chat_client_ready": self.chat_client is not None,
        }

ai_service = AIService()
