import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

@pytest.mark.asyncio
async def test_optimize_uses_previous_code(monkeypatch):
    called = {"messages": None}

    async def fake_llm(*args, **kwargs):
        messages = kwargs.get("messages", args[0] if args else None)
        called["messages"] = messages
        return "### ОПТИМИЗИРОВАННЫЙ НАБОР\nprint('ok')"

    monkeypatch.setattr("backend.main.call_evolution", fake_llm)

    prev = "def test_x(): pass"
    r = client.post(
        "/generate",
        json={"type": "optimize", "previous_code": prev}
    )

    assert r.status_code == 200
    data = r.json()
    assert data["validation"]["valid"] is True

    assert prev in called["messages"][0]["content"]

    assert data["code"] == "print('ok')"


@pytest.mark.asyncio
async def test_optimize_skips_python_validation(monkeypatch):
    async def fake_llm(*args, **kwargs):
        return "not_python_but_allowed"

    monkeypatch.setattr("backend.main.call_evolution", fake_llm)

    r = client.post(
        "/generate",
        json={"type": "optimize", "previous_code": "abc"}
    )

    assert r.status_code == 200
    assert r.json()["validation"]["valid"] is True
    assert r.json()["validation"]["message"].startswith("Тест-план / оптимизация")