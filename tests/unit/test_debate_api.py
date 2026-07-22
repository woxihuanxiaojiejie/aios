from __future__ import annotations

from datetime import timedelta

from fastapi.testclient import TestClient
from tests.factories import fixed_now, make_evidence

from aios.api.app import create_app
from aios.kernel.decision import Decision
from aios.storage.memory import InMemoryStorage


def client() -> tuple[TestClient, InMemoryStorage]:
    storage = InMemoryStorage()
    return TestClient(create_app(storage=storage)), storage


def create_session(
    api: TestClient, storage: InMemoryStorage, suffix: str
) -> tuple[str, str]:
    symbol = f"6005{suffix}"
    watchlist = api.post(
        "/api/v1/research/watchlist",
        json={"symbol": symbol, "market": "CN"},
    ).json()
    evidence = make_evidence(
        evidence_id=f"ev_00000000-0000-0000-0000-000000000{suffix}"
    ).model_copy(update={"symbols": (symbol,)})
    storage.save(evidence)
    session = api.post(
        "/api/v1/research/sessions",
        json={
            "watchlist_item_id": watchlist["watchlist_item_id"],
            "horizon_days": 3,
            "as_of": (fixed_now() + timedelta(hours=int(suffix))).isoformat(),
            "evidence_ids": [evidence.evidence_id],
        },
    ).json()
    return session["research_session_id"], evidence.evidence_id


def create_report(
    api: TestClient,
    session_id: str,
    evidence_id: str,
    *,
    role: str = "technical",
) -> dict[str, object]:
    response = api.post(
        f"/api/v1/research/sessions/{session_id}/agent-reports",
        json={
            "role": role,
            "summary": "trend",
            "stance": "watch",
            "confidence": 0.7,
            "evidence_ids": [evidence_id],
            "source": "manual",
        },
    )
    assert response.status_code == 201
    return response.json()


def create_hypothesis(
    api: TestClient,
    session_id: str,
    report_id: str,
    evidence_id: str,
) -> dict[str, object]:
    response = api.post(
        f"/api/v1/research/sessions/{session_id}/hypotheses",
        json={
            "statement": "Demand improves",
            "rationale": "report",
            "direction": "bullish",
            "horizon_days": 3,
            "confidence": 0.55,
            "supporting_report_ids": [report_id],
            "supporting_evidence_ids": [evidence_id],
        },
    )
    assert response.status_code == 201
    return response.json()


def seed_debate_inputs(
    api: TestClient,
    storage: InMemoryStorage,
    suffix: str = "001",
) -> tuple[str, str, str, str]:
    session_id, evidence_id = create_session(api, storage, suffix)
    report = create_report(api, session_id, evidence_id)
    hypothesis = create_hypothesis(
        api,
        session_id,
        str(report["report_id"]),
        evidence_id,
    )
    return (
        session_id,
        str(report["report_id"]),
        str(hypothesis["hypothesis_id"]),
        evidence_id,
    )


def create_debate(api: TestClient, session_id: str) -> dict[str, object]:
    response = api.post(f"/api/v1/research/sessions/{session_id}/debates")
    assert response.status_code == 201
    return response.json()


def create_proposal(
    api: TestClient,
    debate_id: str,
    hypothesis_id: str,
    evidence_id: str,
    *,
    conclusion: str = "buy",
) -> dict[str, object]:
    response = api.post(
        f"/api/v1/research/debates/{debate_id}/proposal",
        json={
            "conclusion": conclusion,
            "confidence": 0.7,
            "thesis": "risk-controlled thesis",
            "supporting_hypothesis_ids": [hypothesis_id],
            "rejected_hypothesis_ids": [],
            "evidence_ids": [evidence_id],
            "risk_notes": ["size small"],
        },
    )
    assert response.status_code == 201
    return response.json()


def test_debate_api_create_get_and_list_freezes_inputs() -> None:
    api, storage = client()
    session_id, report_id, hypothesis_id, _evidence_id = seed_debate_inputs(
        api, storage
    )

    debate = create_debate(api, session_id)

    assert debate["debate_id"].startswith("db_")
    assert debate["research_session_id"] == session_id
    assert debate["report_ids"] == [report_id]
    assert debate["hypothesis_ids"] == [hypothesis_id]
    assert debate["status"] == "open"

    assert api.get(f"/api/v1/research/debates/{debate['debate_id']}").json() == debate
    assert api.get(f"/api/v1/research/sessions/{session_id}/debates").json()[
        "items"
    ] == [debate]

    late_report = create_report(api, session_id, _evidence_id, role="fundamental")
    assert late_report["report_id"] not in debate["report_ids"]
    assert api.get(f"/api/v1/research/debates/{debate['debate_id']}").json()[
        "report_ids"
    ] == [report_id]


def test_debate_api_rejects_cancelled_session_and_bad_references() -> None:
    api, storage = client()
    session_id, report_id, hypothesis_id, evidence_id = seed_debate_inputs(api, storage)
    other_session_id, other_report_id, other_hypothesis_id, other_evidence_id = (
        seed_debate_inputs(api, storage, "002")
    )
    debate = create_debate(api, session_id)

    bad_statement = api.post(
        f"/api/v1/research/debates/{debate['debate_id']}/statements",
        json={
            "agent_report_id": other_report_id,
            "hypothesis_id": hypothesis_id,
            "stance": "support",
            "reasoning": "bad report",
            "evidence_ids": [evidence_id],
            "confidence_before": 0.5,
            "confidence_after": 0.6,
        },
    )
    assert bad_statement.status_code == 400
    assert bad_statement.json()["error"]["code"] == "reference_integrity_error"

    bad_hypothesis = api.post(
        f"/api/v1/research/debates/{debate['debate_id']}/statements",
        json={
            "agent_report_id": report_id,
            "hypothesis_id": other_hypothesis_id,
            "stance": "support",
            "reasoning": "bad hypothesis",
            "evidence_ids": [evidence_id],
            "confidence_before": 0.5,
            "confidence_after": 0.6,
        },
    )
    assert bad_hypothesis.status_code == 400
    assert bad_hypothesis.json()["error"]["code"] == "reference_integrity_error"

    bad_proposal = api.post(
        f"/api/v1/research/debates/{debate['debate_id']}/proposal",
        json={
            "conclusion": "buy",
            "confidence": 0.7,
            "thesis": "bad proposal",
            "supporting_hypothesis_ids": [hypothesis_id],
            "rejected_hypothesis_ids": [],
            "evidence_ids": [other_evidence_id],
            "risk_notes": [],
        },
    )
    assert bad_proposal.status_code == 400
    assert bad_proposal.json()["error"]["code"] == "reference_integrity_error"

    cancelled = api.post(f"/api/v1/research/sessions/{other_session_id}/cancel")
    assert cancelled.status_code == 200
    cancelled_debate = api.post(f"/api/v1/research/sessions/{other_session_id}/debates")
    assert cancelled_debate.status_code == 409
    assert cancelled_debate.json()["error"]["code"] == "invalid_state_transition"


def test_debate_statement_and_proposal_conflicts() -> None:
    api, storage = client()
    session_id, report_id, hypothesis_id, evidence_id = seed_debate_inputs(api, storage)
    debate = create_debate(api, session_id)

    statement = api.post(
        f"/api/v1/research/debates/{debate['debate_id']}/statements",
        json={
            "agent_report_id": report_id,
            "hypothesis_id": hypothesis_id,
            "stance": "support",
            "reasoning": "supports",
            "evidence_ids": [evidence_id],
            "confidence_before": 0.5,
            "confidence_after": 0.6,
        },
    )
    assert statement.status_code == 201
    duplicate_statement = api.post(
        f"/api/v1/research/debates/{debate['debate_id']}/statements",
        json={
            "agent_report_id": report_id,
            "hypothesis_id": hypothesis_id,
            "stance": "neutral",
            "reasoning": "again",
            "evidence_ids": [],
            "confidence_before": 0.5,
            "confidence_after": 0.5,
        },
    )
    assert duplicate_statement.status_code == 409
    assert duplicate_statement.json()["error"]["code"] == "entity_conflict"

    proposal = create_proposal(
        api,
        str(debate["debate_id"]),
        hypothesis_id,
        evidence_id,
    )
    duplicate_proposal = api.post(
        f"/api/v1/research/debates/{debate['debate_id']}/proposal",
        json={
            "conclusion": "watch",
            "confidence": 0.5,
            "thesis": "second",
            "supporting_hypothesis_ids": [hypothesis_id],
            "rejected_hypothesis_ids": [],
            "evidence_ids": [evidence_id],
            "risk_notes": [],
        },
    )
    assert proposal["proposal_id"].startswith("dp_")
    assert duplicate_proposal.status_code == 409
    assert duplicate_proposal.json()["error"]["code"] == "entity_conflict"


def test_risk_review_api_rules_and_one_review_per_proposal() -> None:
    api, storage = client()
    session_id, _report_id, hypothesis_id, evidence_id = seed_debate_inputs(
        api, storage
    )
    debate = create_debate(api, session_id)
    proposal = create_proposal(
        api, str(debate["debate_id"]), hypothesis_id, evidence_id
    )

    bad_approve = api.post(
        f"/api/v1/research/proposals/{proposal['proposal_id']}/risk-review",
        json={
            "verdict": "approve",
            "final_conclusion": "watch",
            "final_confidence": 0.6,
            "reasons": ["changed conclusion"],
        },
    )
    assert bad_approve.status_code == 409
    assert bad_approve.json()["error"]["code"] == "invalid_state_transition"

    confidence_increase = api.post(
        f"/api/v1/research/proposals/{proposal['proposal_id']}/risk-review",
        json={
            "verdict": "approve",
            "final_conclusion": "buy",
            "final_confidence": 0.8,
            "reasons": ["higher confidence"],
        },
    )
    assert confidence_increase.status_code == 409

    review = api.post(
        f"/api/v1/research/proposals/{proposal['proposal_id']}/risk-review",
        json={
            "verdict": "approve",
            "final_conclusion": "buy",
            "final_confidence": 0.7,
            "reasons": ["approved"],
        },
    )
    assert review.status_code == 201

    duplicate_review = api.post(
        f"/api/v1/research/proposals/{proposal['proposal_id']}/risk-review",
        json={
            "verdict": "downgrade",
            "final_conclusion": "watch",
            "final_confidence": 0.5,
            "reasons": ["second review"],
        },
    )
    assert duplicate_review.status_code == 409
    assert duplicate_review.json()["error"]["code"] == "entity_conflict"


def test_finalize_api_creates_assembly_and_is_idempotent() -> None:
    api, storage = client()
    session_id, report_id, hypothesis_id, evidence_id = seed_debate_inputs(api, storage)
    debate = create_debate(api, session_id)
    proposal = create_proposal(
        api, str(debate["debate_id"]), hypothesis_id, evidence_id
    )
    risk = api.post(
        f"/api/v1/research/proposals/{proposal['proposal_id']}/risk-review",
        json={
            "verdict": "downgrade",
            "final_conclusion": "watch",
            "final_confidence": 0.5,
            "reasons": ["risk downgrade"],
        },
    ).json()

    assembly = api.post(
        f"/api/v1/research/proposals/{proposal['proposal_id']}/finalize"
    )
    second = api.post(f"/api/v1/research/proposals/{proposal['proposal_id']}/finalize")

    assert assembly.status_code == 200
    assert second.status_code == 200
    assert second.json() == assembly.json()
    assert len(storage.list(Decision)) == 1
    body = assembly.json()
    assert body["research_session_id"] == session_id
    assert body["debate_id"] == debate["debate_id"]
    assert body["proposal_id"] == proposal["proposal_id"]
    assert body["risk_review_id"] == risk["risk_review_id"]
    assert body["report_ids"] == [report_id]
    assert body["hypothesis_ids"] == [hypothesis_id]
    assert body["evidence_ids"] == [evidence_id]
    decision = storage.get(Decision, body["decision_id"])
    assert decision.action.value == "observe"
    assert decision.status.value == "proposed"


def test_finalize_invalid_api_maps_to_no_trade_invalid_decision() -> None:
    api, storage = client()
    session_id, _report_id, hypothesis_id, evidence_id = seed_debate_inputs(
        api, storage
    )
    debate = create_debate(api, session_id)
    proposal = create_proposal(
        api, str(debate["debate_id"]), hypothesis_id, evidence_id
    )
    api.post(
        f"/api/v1/research/proposals/{proposal['proposal_id']}/risk-review",
        json={
            "verdict": "veto",
            "final_conclusion": "invalid",
            "final_confidence": 0.1,
            "reasons": ["invalid setup"],
        },
    )

    assembly = api.post(
        f"/api/v1/research/proposals/{proposal['proposal_id']}/finalize"
    ).json()
    decision = storage.get(Decision, assembly["decision_id"])

    assert assembly["conclusion"] == "invalid"
    assert decision.action.value == "no_trade"
    assert decision.status.value == "invalid"


def test_debate_api_missing_entities_return_not_found() -> None:
    api, _storage = client()

    missing_session = api.post("/api/v1/research/sessions/rs_missing/debates")
    missing_debate = api.get("/api/v1/research/debates/db_missing")
    missing_statement_debate = api.post(
        "/api/v1/research/debates/db_missing/statements",
        json={
            "agent_report_id": "ar_missing",
            "hypothesis_id": "hp_missing",
            "stance": "support",
            "reasoning": "missing",
            "evidence_ids": [],
            "confidence_before": 0.5,
            "confidence_after": 0.6,
        },
    )
    missing_proposal_review = api.post(
        "/api/v1/research/proposals/dp_missing/risk-review",
        json={
            "verdict": "approve",
            "final_conclusion": "buy",
            "final_confidence": 0.5,
            "reasons": ["missing"],
        },
    )
    missing_proposal_finalize = api.post(
        "/api/v1/research/proposals/dp_missing/finalize"
    )

    assert missing_session.status_code == 404
    assert missing_debate.status_code == 404
    assert missing_statement_debate.status_code == 404
    assert missing_proposal_review.status_code == 404
    assert missing_proposal_finalize.status_code == 404
    assert missing_session.json()["error"]["code"] == "entity_not_found"
