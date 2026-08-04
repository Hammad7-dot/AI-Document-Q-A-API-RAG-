# Project Blockers

Version: 1.0

Project: AI Document Q&A API (RAG)

Status: Active

---

# Purpose

This document tracks all blockers that prevent or delay implementation.

Each blocker should include

- Status
- Owner
- Priority
- Impact
- Resolution
- Date Updated

---

# Status Legend

🟢 Resolved

🟡 In Progress

🔴 Blocked

⚪ Waiting

---

# BLOCKER-001

Title

OpenAI API Key

Status

🔴 Blocked

Priority

High

Impact

Cannot generate embeddings or chat responses using OpenAI.

Resolution

Configure

OPENAI_API_KEY

inside

.env

Owner

Developer

---

# BLOCKER-002

Title

PostgreSQL pgvector Extension

Status

🟡 In Progress

Priority

High

Impact

Vector search unavailable.

Resolution

Enable

CREATE EXTENSION vector;

Verify Docker image includes pgvector.

Owner

Backend Developer

---

# BLOCKER-003

Title

Redis Connection

Status

⚪ Waiting

Priority

Medium

Impact

Caching unavailable.

Resolution

Configure Redis service in Docker Compose.

Verify health check.

Owner

Backend Developer

---

# BLOCKER-004

Title

Large PDF Parsing

Status

⚪ Waiting

Priority

Medium

Impact

Large PDFs may exceed processing time.

Possible Solutions

- Background worker
- Celery
- Async processing
- Progress tracking

Owner

Backend Developer

---

# BLOCKER-005

Title

Streaming Responses

Status

⚪ Waiting

Priority

Medium

Impact

Frontend cannot display incremental AI responses.

Resolution

Implement Server-Sent Events (SSE).

Owner

Backend Developer

---

# BLOCKER-006

Title

Authentication Middleware

Status

⚪ Waiting

Priority

High

Impact

Protected endpoints unavailable.

Resolution

Implement JWT verification middleware.

Owner

Backend Developer

---

# BLOCKER-007

Title

Conversation Memory

Status

⚪ Waiting

Priority

Medium

Impact

Chat history unavailable.

Resolution

Design conversation schema.

Store conversations in PostgreSQL.

---

# BLOCKER-008

Title

Document Chunking Strategy

Status

🟡 In Progress

Priority

High

Impact

Poor retrieval quality.

Options

- RecursiveCharacterTextSplitter
- TokenTextSplitter
- Semantic Chunking

Decision Pending

Benchmark retrieval quality.

---

# BLOCKER-009

Title

Embedding Model Selection

Status

🟡 In Progress

Priority

Medium

Impact

Changing embedding models requires re-indexing documents.

Candidates

- text-embedding-3-small
- BAAI/bge-small-en
- nomic-embed-text

Decision

Pending benchmark.

---

# BLOCKER-010

Title

Production Deployment

Status

⚪ Waiting

Priority

Medium

Impact

Application not deployable.

Tasks

- Docker optimization
- Environment variables
- Reverse proxy
- HTTPS
- Monitoring

---

# External Dependencies

## OpenAI

Required

Embeddings

Chat Completion

Status

Waiting

---

## PostgreSQL

Required

Database

Status

Waiting

---

## Redis

Required

Caching

Status

Waiting

---

## Ollama

Optional

Local LLM

Status

Optional

---

# Technical Risks

Risk

Large PDFs consume excessive memory.

Mitigation

Streaming parser.

---

Risk

Embedding generation is slow.

Mitigation

Background workers.

---

Risk

High API costs.

Mitigation

Support local models.

---

Risk

Slow vector search.

Mitigation

Vector indexes.

---

Risk

Prompt injection.

Mitigation

Input validation and prompt hardening.

---

Risk

Unauthorized document access.

Mitigation

Multi-tenant authorization checks.

---

# Pending Decisions

- Final embedding model
- Final LLM
- OCR support
- Hybrid search
- Background job framework
- Deployment platform
- Monitoring stack
- Rate limiting strategy

---

# Exit Criteria

The project is considered unblocked when

- PostgreSQL is operational
- pgvector is enabled
- Redis is connected
- Authentication works
- Embeddings are generated
- Semantic search returns relevant results
- Chat endpoint functions correctly
- Streaming responses work
- Docker Compose starts all services successfully