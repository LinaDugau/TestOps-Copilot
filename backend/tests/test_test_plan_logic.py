import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

@pytest.mark.asyncio
async def test_test_plan_injects_previous_code(monkeypatch):
    called = {"msg": None}

    async def fake_llm(*args, **kwargs):
        messages = kwargs.get("messages", args[0] if args else None)
        called["msg"] = messages[0]["content"]
        return "# Тест-план\nOK"

    monkeypatch.setattr("backend.main.call_evolution", fake_llm)

    prev = "class TestX: pass"

    r = client.post("/generate", json={"type": "test_plan", "previous_code": prev})

    assert r.status_code == 200
    assert prev in called["msg"]
    assert "Тест-план" in r.json()["code"]

@pytest.mark.asyncio
async def test_test_plan_skips_python_validation(monkeypatch):
    async def fake_llm(*args, **kwargs):
        return "not_python_and_no_problem"

    monkeypatch.setattr("backend.main.call_evolution", fake_llm)

    r = client.post("/generate", json={"type": "test_plan", "previous_code": "abc"})

    assert r.status_code == 200
    assert r.json()["validation"]["valid"] is True
    assert "валидация не требуется" in r.json()["validation"]["message"]