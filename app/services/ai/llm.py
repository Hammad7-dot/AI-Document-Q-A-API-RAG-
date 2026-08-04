"""LLM provider abstraction (OpenAI default, Ollama optional)."""
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator

from langchain_groq import ChatGroq
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings

SYSTEM_PROMPT = (
    "You are a helpful assistant that answers questions strictly using the "
    "provided document context. If the answer is not contained in the context, "
    "say you don't know based on the document. Always cite which context "
    "snippet(s) support your answer."
)


class LLMProvider(ABC):
    """Abstract interface for chat completion generation."""

    @abstractmethod
    async def generate(self, question: str, context: str) -> str:
        ...

    @abstractmethod
    async def stream(self, question: str, context: str) -> AsyncIterator[str]:
        ...

    @staticmethod
    def _build_messages(question: str, context: str) -> list:
        user_prompt = (
            f"Context:\n{context}\n\n"
            f"Question: {question}\n\n"
            "Answer using only the context above."
        )
        return [SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=user_prompt)]


class OpenAILLMProvider(LLMProvider):
    def __init__(self) -> None:
        self._client = ChatOpenAI(
            model=settings.openai_chat_model,
            api_key=settings.openai_api_key or "not-set",
            temperature=settings.llm_temperature,
        )

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8))
    async def generate(self, question: str, context: str) -> str:
        messages = self._build_messages(question, context)
        response = await self._client.ainvoke(messages)
        return response.content

    async def stream(self, question: str, context: str) -> AsyncIterator[str]:
        messages = self._build_messages(question, context)
        async for chunk in self._client.astream(messages):
            if chunk.content:
                yield chunk.content


class GroqLLMProvider(LLMProvider):
    def __init__(self) -> None:
        self._client = ChatGroq(
            model=settings.groq_chat_model,
            api_key=settings.groq_api_key or "not-set",
            temperature=settings.llm_temperature,
        )

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8))
    async def generate(self, question: str, context: str) -> str:
        messages = self._build_messages(question, context)
        response = await self._client.ainvoke(messages)
        return response.content

    async def stream(self, question: str, context: str) -> AsyncIterator[str]:
        messages = self._build_messages(question, context)
        async for chunk in self._client.astream(messages):
            if chunk.content:
                yield chunk.content


class OllamaLLMProvider(LLMProvider):
    def __init__(self) -> None:
        self._client = ChatOllama(
            model=settings.ollama_chat_model,
            base_url=settings.ollama_base_url,
            temperature=settings.llm_temperature,
        )

    async def generate(self, question: str, context: str) -> str:
        messages = self._build_messages(question, context)
        response = await self._client.ainvoke(messages)
        return response.content

    async def stream(self, question: str, context: str) -> AsyncIterator[str]:
        messages = self._build_messages(question, context)
        async for chunk in self._client.astream(messages):
            if chunk.content:
                yield chunk.content


def get_llm_provider() -> LLMProvider:
    """Factory returning the configured LLM provider."""
    if settings.llm_provider == "ollama":
        return OllamaLLMProvider()
    if settings.llm_provider == "groq":
        return GroqLLMProvider()
    return OpenAILLMProvider()
