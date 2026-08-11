"""Embedding provider abstraction (OpenAI default, Ollama optional)."""
from abc import ABC, abstractmethod

from langchain_cohere import CohereEmbeddings
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_ollama import OllamaEmbeddings
from langchain_openai import OpenAIEmbeddings
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings


class EmbeddingProvider(ABC):
    """Abstract interface for text embedding generation."""

    @abstractmethod
    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        ...

    @abstractmethod
    async def embed_query(self, text: str) -> list[float]:
        ...


class OpenAIEmbeddingProvider(EmbeddingProvider):
    def __init__(self) -> None:
        self._client = OpenAIEmbeddings(
            model=settings.openai_embedding_model,
            api_key=settings.openai_api_key or "not-set",
        )

    @retry(stop=stop_after_attempt(6), wait=wait_exponential(multiplier=2, min=2, max=60))
    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return await self._client.aembed_documents(texts)

    @retry(stop=stop_after_attempt(6), wait=wait_exponential(multiplier=2, min=2, max=60))
    async def embed_query(self, text: str) -> list[float]:
        return await self._client.aembed_query(text)


class GoogleEmbeddingProvider(EmbeddingProvider):
    def __init__(self) -> None:
        self._client = GoogleGenerativeAIEmbeddings(
            model=settings.google_embedding_model,
            google_api_key=settings.google_api_key or "not-set",
        )

    @retry(stop=stop_after_attempt(6), wait=wait_exponential(multiplier=2, min=2, max=60))
    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return await self._client.aembed_documents(texts)

    @retry(stop=stop_after_attempt(6), wait=wait_exponential(multiplier=2, min=2, max=60))
    async def embed_query(self, text: str) -> list[float]:
        return await self._client.aembed_query(text)


class CohereEmbeddingProvider(EmbeddingProvider):
    def __init__(self) -> None:
        self._client = CohereEmbeddings(
            model=settings.cohere_embedding_model,
            cohere_api_key=settings.cohere_api_key or "not-set",
        )

    @retry(stop=stop_after_attempt(6), wait=wait_exponential(multiplier=2, min=2, max=60))
    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return await self._client.aembed_documents(texts)

    @retry(stop=stop_after_attempt(6), wait=wait_exponential(multiplier=2, min=2, max=60))
    async def embed_query(self, text: str) -> list[float]:
        return await self._client.aembed_query(text)


class OllamaEmbeddingProvider(EmbeddingProvider):
    def __init__(self) -> None:
        self._client = OllamaEmbeddings(
            model=settings.ollama_embedding_model, base_url=settings.ollama_base_url
        )

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return await self._client.aembed_documents(texts)

    async def embed_query(self, text: str) -> list[float]:
        return await self._client.aembed_query(text)


def get_embedding_provider() -> EmbeddingProvider:
    """Factory returning the configured embedding provider."""
    if settings.embedding_provider == "ollama":
        return OllamaEmbeddingProvider()
    if settings.embedding_provider == "google":
        return GoogleEmbeddingProvider()
    if settings.embedding_provider == "cohere":
        return CohereEmbeddingProvider()
    return OpenAIEmbeddingProvider()
