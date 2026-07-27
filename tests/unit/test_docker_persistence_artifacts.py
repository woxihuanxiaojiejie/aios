from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_docker_compose_uses_named_postgres_volume() -> None:
    compose = (ROOT / "docker-compose.yml").read_text()

    assert "tmpfs:" not in compose
    assert "PGDATA: /var/lib/postgresql/data/pgdata" in compose
    assert "aios_postgres_data:" in compose
    assert "aios_postgres_data:/var/lib/postgresql/data/pgdata" in compose
    assert "driver: local" in compose
    assert "driver_opts:" in compose
    assert "device: ${AIOS_POSTGRES_VOLUME_DIR:-/tmp/aios-postgres-data}" in compose


def test_docker_compose_runs_scheduler_as_independent_service() -> None:
    compose = (ROOT / "docker-compose.yml").read_text()

    assert "scheduler:" in compose
    assert "uv run aios scheduler serve" in compose
    assert "research_due_scan" not in compose
    assert "redis:" not in compose.lower()
    assert "rabbitmq:" not in compose.lower()
    assert "celery" not in compose.lower()
    assert "rq worker" not in compose.lower()


def test_docker_persistence_script_is_safe_and_repeatable() -> None:
    script = (ROOT / "scripts" / "verify_docker_persistence.sh").read_text()

    assert "docker compose down -v" not in script
    assert "docker volume rm" not in script
    assert "docker compose restart postgres backend scheduler" in script
    assert "docker compose up -d --build postgres backend scheduler frontend" in script
    assert "wait_for_frontend" in script
    assert "docker compose down" in script
    assert "COMPOSE_PROJECT_NAME" in script
    assert "AIOS_POSTGRES_VOLUME_DIR" in script
    assert "mkdir -p" in script
    assert "chmod 700" in script
    assert "chown 70:70" in script
    assert "curl" in script
