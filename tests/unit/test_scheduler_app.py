from __future__ import annotations

import os

from aios.application.scheduler_app import _load_runtime_env


def test_scheduler_runtime_loads_dotenv(monkeypatch, tmp_path) -> None:
    dotenv = tmp_path / ".env"
    dotenv.write_text(
        "AIOS_EXTERNAL_LLM_MODEL=deepseek/deepseek-v4-pro\nDEEPSEEK_API_KEY=test-key\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("AIOS_EXTERNAL_LLM_MODEL", raising=False)
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)

    _load_runtime_env()

    assert os.environ["AIOS_EXTERNAL_LLM_MODEL"] == "deepseek/deepseek-v4-pro"
    assert os.environ["DEEPSEEK_API_KEY"] == "test-key"
