# ADR 0001: PostgreSQL Storage Adapter

## Status

Accepted.

## Context

AIOS V0.1 keeps the kernel focused on the decision lifecycle:
Evidence -> Experiment -> Decision -> Review -> Learning. TASK 002 adds durable
storage without changing kernel semantics or binding the domain model to a
database framework.

## Decision

The kernel remains independent of SQLAlchemy and PostgreSQL. Domain entities are
Pydantic models. PostgreSQL persistence is implemented as a storage adapter that
conforms to the existing storage protocol.

We use PostgreSQL because AIOS needs durable JSONB fields, relational integrity
for Experiment/Decision/Review/Learning ownership, and database-level
constraints for critical invariants. SQLAlchemy 2.x provides a mature
synchronous ORM boundary for table records, while Alembic provides explicit,
reversible schema migrations instead of application startup schema creation.

V0.1 stores `evidence_ids` as JSONB on Experiment and Decision. This matches the
current kernel object shape and avoids introducing association tables before the
query model is known. Lifecycle services still validate referenced Evidence
objects before saving.

Foreign keys use `ON DELETE RESTRICT` rather than cascade deletion. Reviews and
Learnings are part of an audit trail for decisions, so removing upstream rows
implicitly would hide historical context.

## Consequences

The mapper layer has some explicit repetition, but the boundary is clear:
Pydantic entities do not inherit ORM classes and ORM records do not leak into
kernel workflows.

Known limitations:

- Evidence references are not database foreign keys in V0.1.
- Query support is limited to `save`, `get`, `list`, and `exists`.
- Migrations must be run before using `PostgresStorage`.
- There is no async storage path, retry framework, caching, or read/write split.
