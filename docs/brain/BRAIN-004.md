# BRAIN-004 - Decision

## Core Question

Which final direction should AIOS select, and why were the alternatives rejected?

## Responsibility

BRAIN-004 is the only Brain that generates the final auditable investment
decision. It consumes existing upstream outputs and does not perform new market
analysis.

## Inputs

- BRAIN-001 Evidence
- BRAIN-002 Skill Results
- BRAIN-003 Discussion Result

## Explicit Boundaries

BRAIN-004 must not:

- call or rerun Skills
- browse, fetch news, or fetch market data
- modify skill definitions or long-term weights
- perform Learning or Settlement
- interact with brokers
- place orders automatically
- generate position sizing, stop-loss, or take-profit plans

Trade Plan, Settlement, and Learning remain separate downstream stages.

## Outputs

`DecisionResult`:

- `direction`
- `confidence`
- `action`
- `reasoning`
- `supporting_skills`
- `opposing_skills`
- `discussion_refs`
- `evidence_refs`
- `risks`
- `rejected_directions`
- `decision_summary`

All reasoning, risk notes, and rejected directions must be traceable to supplied
Skill IDs, Discussion refs, or Evidence IDs.
