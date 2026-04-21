import asyncio
import os
from typing import Dict, List

from dotenv import load_dotenv

load_dotenv()


def _get_llm(model: str = "gpt-4o-mini", temperature: float = 0.0):
    """Factory: swap provider via env LLM_PROVIDER (openai | google | anthropic)."""
    provider = os.getenv("LLM_PROVIDER", "openai").lower()
    if provider == "google":
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(model=model, temperature=temperature)
    elif provider == "anthropic":
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(model="claude-3-5-haiku-20241022", temperature=temperature)
    else:
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(model=model, temperature=temperature)


def _get_vectorstore(persist_dir: str = "chroma_db", collection_name: str = "day09_docs"):
    """Load existing ChromaDB."""
    from langchain_chroma import Chroma
    from langchain_openai import OpenAIEmbeddings

    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    return Chroma(
        persist_directory=persist_dir,
        collection_name=collection_name,
        embedding_function=embeddings,
    )


class RagAgentV1:
    """
    RAG Agent V1 — Base version (intentionally weak).
    - top_k=2 (ít context)
    - Generic prompt (không có hướng dẫn cụ thể)
    - Không rerank, không filter
    """

    def __init__(self):
        self.name = "SupportAgent-v1"
        self.vectorstore = _get_vectorstore()
        self.llm = _get_llm()

    async def query(self, question: str) -> Dict:
        # Simple retrieval — only top 2
        docs = self.vectorstore.similarity_search(question, k=2)

        contexts = [doc.page_content for doc in docs]
        retrieved_ids = [
            doc.metadata.get("source", doc.metadata.get("id", f"doc_{i}"))
            for i, doc in enumerate(docs)
        ]

        # Generic prompt — no special instructions
        context_text = "\n---\n".join(contexts)
        prompt = f"Dựa vào tài liệu sau, trả lời câu hỏi.\n\nTài liệu:\n{context_text}\n\nCâu hỏi: {question}\n\nTrả lời:"

        response = await asyncio.to_thread(self.llm.invoke, prompt)
        answer = response.content

        return {
            "answer": answer,
            "contexts": contexts,
            "retrieved_ids": retrieved_ids,
            "metadata": {
                "model": self.llm.model_name if hasattr(self.llm, "model_name") else str(self.llm),
                "top_k": 2,
                "version": "v1",
                "sources": retrieved_ids,
            },
        }
