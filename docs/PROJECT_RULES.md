# PROJECT_RULES.md

# AIOS Project Development Rules

> These rules are mandatory for all AI coding assistants working on this repository.

---

# Rule 001 — Open Source First

Always search for mature open-source solutions before implementing new features.

Priority:

1. Reuse
2. Adapter
3. Plugin
4. Original Implementation

Original implementation is allowed only if:

- No mature open-source solution exists.
- Existing solutions cannot satisfy AIOS business requirements.
- License or performance makes reuse unsuitable.

---

# Rule 002 — Never Reinvent the Wheel

Do NOT reimplement existing mature capabilities.

Examples include but are not limited to:

- Agent Runtime
- Multi-Agent Framework
- Workflow Engine
- Tool Routing
- LLM Provider
- Backtesting Engine
- Market Data Loader
- Report Generator
- Memory Framework

Reuse existing implementations whenever possible.

---

# Rule 003 — AIOS Original Scope

AIOS should focus on its unique business logic.

Priority areas include:

- Decision Protocol
- Debate Protocol
- Weight Engine
- Responsibility Attribution
- Settlement
- Learning Engine
- Evidence Lifecycle
- Factor Evolution

Only these components should contain substantial original logic.

---

# Rule 004 — Adapter First

When integrating external projects:

Preferred order:

Adapter > Plugin > Fork

Avoid modifying third-party source code whenever possible.

---

# Rule 005 — Single Responsibility

Each module should have only one responsibility.

Examples:

- Brain handles decision logic.
- Adapter handles integration.
- API handles communication.
- Database handles persistence.

Do not mix responsibilities.

---

# Rule 006 — Interface First

Business logic must depend on interfaces rather than concrete implementations.

Avoid hard dependencies on any specific framework.

This allows replacing third-party components in the future.

---

# Rule 007 — Traceability

Every prediction must be traceable.

Required chain:

Evidence

↓

Hypothesis

↓

Agent Analysis

↓

Debate

↓

Decision

↓

Trade Plan

↓

Settlement

↓

Evaluation

↓

Learning

No black-box decisions.

---

# Rule 008 — Structured Output

All AI outputs should be structured whenever possible.

Preferred formats:

- JSON
- Pydantic Models
- Typed Objects

Avoid long unstructured text for machine-readable results.

---

# Rule 009 — Minimize Architecture Changes

Do not modify the project architecture merely to complete a task.

If a task requires:

- changing core architecture
- replacing existing modules
- introducing new infrastructure

the AI must explain the proposal before implementation.

---

# Rule 010 — Reuse Verification

Before writing new code, always check:

- Can an existing module be reused?
- Can an existing interface be extended?
- Can an open-source project solve this?
- Is an Adapter sufficient?

Only implement new code after these questions have been answered.

---

# Rule 011 — Keep It Simple

Prefer the simplest solution that satisfies the requirements.

Avoid unnecessary abstraction.

Avoid over-engineering.

Avoid premature optimization.

---

# Rule 012 — Long-Term Maintainability

Code should prioritize:

- readability
- modularity
- testability
- replaceability
- maintainability

Short-term convenience must never compromise long-term architecture.

---

# Rule 013 — AI Development Workflow

Every implementation should follow this order:

Requirement

↓

Search Existing Implementation

↓

Evaluate Reuse

↓

Design

↓

Implement

↓

Test

↓

Document

Never skip the reuse evaluation step.

---

# Rule 014 — Preserve Existing Architecture

Unless explicitly requested:

- do not rename major modules
- do not reorganize project structure
- do not replace existing implementations
- do not introduce breaking changes

Prefer incremental improvements.

---

# Rule 015 — Evidence Over Assumption

Never assume behavior.

Use:

- source code
- official documentation
- tests
- verified APIs

instead of speculation.

If uncertain, explain the uncertainty rather than inventing behavior.

---

# Rule 016 — Architecture Principle
Brain 表示 AI 的思考阶段，而不是功能模块。

新增页面、Agent、数据源、工具、知识库、策略或能力，不得新增 Brain。

只有当 AI 的核心思考流程发生变化时，才允许修改 BRAIN-001～BRAIN-005。

Brain 的数量应长期保持稳定。