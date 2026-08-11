# Development Rules

Version 1.0

---

# Architecture Rules

Use Clean Architecture

Never place business logic inside FastAPI routes.

Routes only call services.

Services call repositories.

Repositories access database.

---

# Code Quality

Follow PEP8

Use type hints everywhere.

Functions should have one responsibility.

Maximum function length

50 lines

Maximum file length

500 lines

---

# Naming

snake_case

Variables

Functions

Files

PascalCase

Classes

UPPER_CASE

Constants

---

# API Rules

Always use async endpoints.

Always return JSON.

Use Pydantic models.

Never expose internal errors.

Use proper HTTP status codes.

---

# Database Rules

Use SQLAlchemy ORM

Never write raw SQL unless necessary.

Every table must have

id

created_at

updated_at

Indexes for

foreign keys

vector columns

---

# Authentication Rules

Passwords

bcrypt

JWT expiration

15 min

Refresh token

7 days

Never store plain passwords.

---

# AI Rules

Chunk size

500 tokens

Overlap

100 tokens

Embedding model configurable

LLM configurable

Temperature

0

Always cite retrieved context.

---

# Redis Rules

Cache embeddings

Cache document metadata

Cache user session

TTL

15 minutes

---

# Logging

Use structured logging.

Never print().

Log

Errors

Warnings

Requests

LLM latency

Embedding latency

---

# Testing Rules

Minimum coverage

80%

Every service

Unit tests

Every endpoint

Integration tests

---

# Git Rules

Feature branches

Meaningful commits

Pull requests required

No direct push to main

---

# Docker Rules

Separate

API

Postgres

Redis

Ollama

Each service has healthcheck.

---

# Documentation

Every public function

Docstring

README updated

API documented automatically

OpenAPI enabled

---

# Performance

Pagination required

Streaming responses

Connection pooling

Async database access

Avoid N+1 queries

---

# Security

Validate every input.

Validate uploaded PDFs.

Limit upload size.

Rate limiting.

JWT verification.

HTTPS in production.

Secrets from environment variables only.

Never hardcode API keys.