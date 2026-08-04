# Architecture Decisions

Version 1.0

---

# ADR-001

Decision

FastAPI

Reason

Excellent async performance and automatic OpenAPI documentation.

---

# ADR-002

Decision

LangChain

Reason

Large ecosystem and flexible RAG pipelines.

Alternative

LlamaIndex

Status

Optional integration.

---

# ADR-003

Decision

PostgreSQL + pgvector

Reason

Reliable relational database with native vector search.

Alternatives

Pinecone

Weaviate

Qdrant

Reason for rejection

Additional infrastructure and vendor lock-in.

---

# ADR-004

Decision

Redis

Reason

Caching and conversation state.

---

# ADR-005

Decision

JWT Authentication

Reason

Stateless authentication suitable for APIs.

---

# ADR-006

Decision

Docker Compose

Reason

Simple local development.

---

# ADR-007

Decision

Chunk Size

500 tokens

Overlap

100 tokens

Reason

Balances retrieval quality and embedding cost.

---

# ADR-008

Decision

Embedding Model

Default

text-embedding-3-small

Alternative

BAAI/bge-small-en

Reason

OpenAI provides excellent retrieval quality while BGE enables local deployments.

---

# ADR-009

Decision

LLM

Default

GPT-4.1 / GPT-5 compatible API

Alternative

Llama 3 via Ollama

Reason

Support both cloud and local inference.

---

# ADR-010

Decision

Conversation History

Store in PostgreSQL.

Reason

Persistent, queryable, and linked to authenticated users.

---

# ADR-011

Decision

Streaming Responses

Use Server-Sent Events (SSE).

Reason

Lower latency and better UX for chat.

---

# ADR-012

Decision

Repository Pattern

Reason

Keeps business logic independent from database implementation.

---

# ADR-013

Decision

Use dependency injection for services.

Reason

Improves testing and modularity.

---

# ADR-014

Decision

Async-first architecture.

Reason

Higher throughput for AI workloads.

---

# ADR-015

Decision

Environment configuration via .env.

Reason

Security and deployment flexibility.

---

# ADR-016

Decision

Store original uploaded PDFs separately from embeddings.

Reason

Allows document re-indexing, metadata extraction, and future OCR support without requiring users to upload files again.

---

# ADR-017

Decision

Multi-tenant data isolation.

Reason

Each authenticated user can only access their own documents, embeddings, and chat history, enforced at both the API and database query levels.

---

# ADR-018

Decision

Observability.

Reason

Use structured logs, health checks, and metrics to monitor embedding generation, retrieval latency, LLM response time, and API performance.