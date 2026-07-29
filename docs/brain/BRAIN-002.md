# BRAIN-002 — Hypothesis Management Engine

## Core Question

What might happen?

## Responsibility

Generate, organize and manage candidate hypotheses.

## Inputs

- Evidence Set
- Historical Experience
- User Goals
- Exploration Signals

## Hypothesis Sources

### 1. Evidence-driven

Generated directly from current evidence.

### 2. Experience-driven

Generated from historical learning and previously validated patterns.

### 3. Goal-driven

Generated according to user-defined long-term research goals.

### 4. Exploration-driven

Generated from unusual observations to discover potential new opportunities.

## Workflow

Evidence

↓

All Professional Agents

↓

Each Agent proposes 0–2 hypotheses

↓

Hypothesis Validation

↓

Merge

↓

Deduplicate

↓

Cluster

↓

Rank

↓

Candidate Hypothesis Set

## Rules

- Every hypothesis must reference supporting evidence.
- Every agent may propose 0–2 hypotheses.
- No hypothesis should be generated without reasoning.
- Minority hypotheses must be preserved.
- Exploration hypotheses are encouraged.

## Outputs

- Candidate Hypothesis Set
- Hypothesis Ranking
- Hypothesis Graph