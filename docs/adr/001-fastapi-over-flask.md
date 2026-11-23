# ADR 001: FastAPI over Flask

Status: Accepted

## Context
Devor is a food delivery backend with I/O-heavy workloads: database queries, Redis, and
real-time order/driver updates (WebSockets). We want async end to end, typed request/response
contracts, and auto-generated API docs for client teams.

## Decision
Use FastAPI (with async SQLAlchemy 2.0 and Pydantic) instead of Flask.

## Consequences
- Native async/await and WebSocket support fit our I/O-bound and real-time needs.
- Pydantic models give validation, typed schemas and OpenAPI docs with no extra glue.
- Dependency injection simplifies sessions, auth and testing.
- Smaller, younger ecosystem than Flask; we must take care not to block the event loop with sync code.
