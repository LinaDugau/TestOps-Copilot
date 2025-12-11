import pytest
from unittest.mock import patch
from backend.cloud_ru import call_evolution, DEFAULT_MODEL

class DummyResponse:
    def __init__(self, text):
        self.choices = [
            type("M", (), {
                "message": type("Msg", (), {"content": text})
            })
        ]

@pytest.mark.asyncio
async def test_call_evolution_success(monkeypatch):
    async def fake_create(*args, **kwargs):
        return DummyResponse("hello")

    class DummyClient:
        class chat:
            class completions:
                create = staticmethod(fake_create)

    monkeypatch.setattr("backend.cloud_ru.client", DummyClient)

    result = await call_evolution([{"role": "user", "content": "hi"}])
    assert result == "hello"


@pytest.mark.asyncio
async def test_call_evolution_empty_response(monkeypatch):
    async def fake_create(*args, **kwargs):
        return DummyResponse(None)

    class DummyClient:
        class chat:
            class completions:
                create = staticmethod(fake_create)

    monkeypatch.setattr("backend.cloud_ru.client", DummyClient)

    with pytest.raises(ValueError):
        await call_evolution([{"role": "user", "content": "hi"}])

@pytest.mark.asyncio
async def test_call_evolution_fallback_model(monkeypatch):
    """Тест fallback на Qwen при ошибке модели из переменной окружения."""
    call_state = {"count": 0}
    initial_model = "ai-sage/GigaChat3-10B-A1.8B"
    fallback_model = DEFAULT_MODEL

    async def fake_create(*args, **kwargs):
        call_state["count"] += 1
        current_model = kwargs.get("model")
        # Первая попытка: кидаем ошибку по модели
        if current_model == initial_model:
            raise Exception(f"Invalid model: {initial_model}")
        if current_model == fallback_model:
            return DummyResponse("fallback success")
        raise Exception(f"Unexpected model: {current_model}")

    class DummyClient:
        class chat:
            class completions:
                create = staticmethod(fake_create)

    monkeypatch.setattr("backend.cloud_ru.client", DummyClient)

    result = await call_evolution([{"role": "user", "content": "hi"}], model=initial_model)
    assert result == "fallback success"
    assert call_state["count"] == 2


@pytest.mark.asyncio
async def test_call_evolution_passes_through_other_errors(monkeypatch):
    """Не модельная ошибка не триггерит fallback и пробрасывается наружу."""
    async def fake_create(*args, **kwargs):
        raise Exception("network timeout")

    class DummyClient:
        class chat:
            class completions:
                create = staticmethod(fake_create)

    monkeypatch.setattr("backend.cloud_ru.client", DummyClient)

    with pytest.raises(Exception) as exc:
        await call_evolution([{"role": "user", "content": "hi"}], model=DEFAULT_MODEL)

    assert "network timeout" in str(exc.value)


@pytest.mark.asyncio
async def test_call_evolution_model_error_without_fallback(monkeypatch):
    """Модельная ошибка при дефолтной модели не уводит в рекурсию."""
    async def fake_create(*args, **kwargs):
        raise Exception("model temporarily unavailable")

    class DummyClient:
        class chat:
            class completions:
                create = staticmethod(fake_create)

    monkeypatch.setattr("backend.cloud_ru.client", DummyClient)

    with pytest.raises(Exception):
        await call_evolution([{"role": "user", "content": "hi"}], model=DEFAULT_MODEL)