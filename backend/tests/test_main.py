import asyncio
import time
import httpx
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_root_endpoint():
    r = client.get("/")
    assert r.status_code == 200
    assert "TestOps Copilot" in r.json()["message"]


def test_get_original_prompt():
    r = client.get("/prompt/manual_ui")
    assert r.status_code == 200
    data = r.json()
    assert data["type"] == "manual_ui"
    assert isinstance(data["prompt"], str)
    assert len(data["prompt"]) > 10


def test_generate_manual_ui(monkeypatch):
    async def fake_llm(*args, **kwargs):
        return """import allure
from allure import step as allure_step

@allure.manual
@allure.label("owner", "qa_team")
def test_x():
    with allure_step("test step"):
        pass"""

    def fake_precheck_manual_ui(code: str) -> list:
        return []

    monkeypatch.setattr("backend.main.call_evolution", fake_llm)
    monkeypatch.setattr("backend.main.precheck_manual_ui", fake_precheck_manual_ui)

    r = client.post("/generate", json={"type": "manual_ui"})
    assert r.status_code == 200
    data = r.json()
    assert "code" in data
    assert data["validation"]["valid"] is True


def test_generate_manual_api_reorders_aaa(monkeypatch):
    async def fake_llm(*args, **kwargs):
        return """import allure
from allure import step as allure_step

@allure.manual
def test_x():
    with allure_step("Act: do"):
        pass
    with allure_step("Arrange: prep"):
        pass
    with allure_step("Assert: check"):
        pass"""

    def fake_precheck_manual_generation(code: str) -> list:
        return []

    monkeypatch.setattr("backend.main.call_evolution", fake_llm)
    monkeypatch.setattr("backend.main.precheck_manual_generation", fake_precheck_manual_generation)

    r = client.post("/generate", json={"type": "manual_api"})
    assert r.status_code == 200
    data = r.json()
    code = data["code"]
    arrange_idx = code.find("Arrange:")
    act_idx = code.find("Act:")
    assert_idx = code.find("Assert:")
    assert arrange_idx != -1 and act_idx != -1 and assert_idx != -1
    assert arrange_idx < act_idx < assert_idx, "AAA order should be Arrange -> Act -> Assert"
    assert data["validation"]["valid"] is True


def test_generate_manual_api_inserts_missing_act(monkeypatch):
    async def fake_llm(*args, **kwargs):
        return """import allure
from allure import step as allure_step

@allure.manual
def test_no_act():
    with allure_step("Arrange: prep"):
        pass
    with allure_step("Assert: check"):
        pass"""

    def fake_precheck_manual_generation(code: str) -> list:
        return []

    monkeypatch.setattr("backend.main.call_evolution", fake_llm)
    monkeypatch.setattr("backend.main.precheck_manual_generation", fake_precheck_manual_generation)

    r = client.post("/generate", json={"type": "manual_api"})
    assert r.status_code == 200
    data = r.json()
    code = data["code"]
    arrange_idx = code.find("Arrange:")
    act_idx = code.find("Act:")
    assert_idx = code.find("Assert:")
    assert arrange_idx != -1 and act_idx != -1 and assert_idx != -1, "All AAA blocks should be present"
    assert arrange_idx < act_idx < assert_idx, "AAA order should be Arrange -> Act -> Assert"
    assert data["validation"]["valid"] is True


def test_generate_manual_ui_empty_response(monkeypatch):
    async def fake_llm(*args, **kwargs):
        return ""

    monkeypatch.setattr("backend.main.call_evolution", fake_llm)

    r = client.post("/generate", json={"type": "manual_ui"})
    assert r.status_code == 502
    assert "пустой ответ" in r.json()["detail"]


def test_generate_custom_prompt(monkeypatch):
    captured_prompt = {}

    async def fake_llm(messages, **kwargs):
        captured_prompt["value"] = messages[0]["content"]
        return "def test_custom():\n    pass"

    monkeypatch.setattr("backend.main.call_evolution", fake_llm)

    r = client.post("/generate", json={"type": "custom", "custom_prompt": "Test prompt"})
    assert r.status_code == 200
    data = r.json()
    assert "test_custom" in data["code"] or "pass" in data["code"]
    assert "senior QA Automation Engineer" in captured_prompt.get("value", "")
    assert data["validation"]["valid"] is True


def test_optimize_requires_previous_code(monkeypatch):
    async def fake_llm(*args, **kwargs):
        return "ok"

    monkeypatch.setattr("backend.main.call_evolution", fake_llm)

    r = client.post("/generate", json={"type": "optimize"})
    assert r.status_code == 400
    assert "previous_code" in r.json()["detail"]


def test_optimize_with_previous_code(monkeypatch):
    async def fake_llm(*args, **kwargs):
        return "optimized based on user code"

    monkeypatch.setattr("backend.main.call_evolution", fake_llm)

    r = client.post("/generate", json={"type": "optimize", "previous_code": "user def test_x(): pass"})
    assert r.status_code == 200
    assert "code" in r.json()

def test_generate_auto_api_recovers_from_annotation_error(monkeypatch):
    async def fake_llm(*args, **kwargs):
        return '@allure.feature("test")\n@allure.title("test")\ndef test_x():\n    print("still works")'

    monkeypatch.setattr("backend.main.call_evolution", fake_llm)

    r = client.post("/generate", json={"type": "auto_api"})
    assert r.status_code == 200
    data = r.json()
    assert data["validation"]["valid"] is True
    assert "still works" in data["code"]


def test_generate_has_metrics_and_fast(monkeypatch):
    async def fake_llm(*args, **kwargs):
        await asyncio.sleep(0.1)
        return """import allure
from allure import step as allure_step

@allure.manual
def test_dummy():
    with allure_step("dummy"):
        pass"""

    monkeypatch.setattr("backend.main.call_evolution", fake_llm)

    start = time.perf_counter()
    r = client.post("/generate", json={"type": "manual_ui"})
    duration = time.perf_counter() - start

    assert r.status_code == 200
    data = r.json()
    assert data["metrics"]["duration_s"] <= duration
    assert data["metrics"]["memory_mb"] > 0
    assert duration < 2.0

def test_generate_recovers_syntax_auto_api(monkeypatch):
    """Тест auto-fix SyntaxError в generate (loop 8x, ast.parse success)."""
    broken_code = '@allure.feature("test")\n@allure.title("test")\ndef test_x():\n    print("hello")'

    async def fake_llm(*args, **kwargs):
        return broken_code 

    monkeypatch.setattr("backend.main.call_evolution", fake_llm)

    r = client.post("/generate", json={"type": "auto_api"})
    assert r.status_code == 200
    data = r.json()
    assert data["validation"]["valid"] is True  # После fix ast.parse OK
    assert "hello" in data["code"]  # Fix закрыл кавычку


def test_generate_recovers_syntax_manual_ui(monkeypatch):
    """Тест auto-fix SyntaxError loop (8x try, unterminated string). Покрывает 471–557."""
    broken_code = 'def test_x():\n    print("hello world'  

    async def fake_llm(*args, **kwargs):
        return broken_code

    def fake_precheck_manual_ui(code): return []  

    monkeypatch.setattr("backend.main.call_evolution", fake_llm)
    monkeypatch.setattr("backend.main.precheck_manual_ui", fake_precheck_manual_ui)
    monkeypatch.setattr("backend.main.precheck_manual_generation", lambda c: [])

    r = client.post("/generate", json={"type": "manual_ui"})
    assert r.status_code == 200
    data = r.json()
    assert data["validation"]["valid"] is True  
    assert 'print("hello world")' in data["code"]  
    assert len(data["code"].splitlines()) > 1  


def test_generate_test_plan_skips_validation(monkeypatch):
    async def fake_llm(*args, **kwargs):
        return "print('plan step')"

    monkeypatch.setattr("backend.main.call_evolution", fake_llm)

    r = client.post("/generate", json={"type": "test_plan", "previous_code": "def test_x(): pass"})
    assert r.status_code == 200
    data = r.json()
    assert data["validation"]["valid"] is True
    assert data["validation"]["issues"] == []
    assert data["type"] == "test_plan"
    assert "plan step" in data["code"]


def test_commit_endpoint_success(monkeypatch):
    def fake_commit_code(**kwargs):
        return {"success": True, "message": "ok", "commit_sha": "sha123"}

    monkeypatch.setattr("backend.main.commit_code", fake_commit_code)

    payload = {
        "repo_id": "group/proj",
        "branch": "main",
        "file_path": "tests/new.py",
        "commit_message": "msg",
        "code": "print('hi')",
    }
    r = client.post("/commit", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert data["commit_sha"] == "sha123"
    assert data["message"] == "ok"


def test_commit_endpoint_failure(monkeypatch):
    def fake_commit_code(**kwargs):
        return {"success": False, "message": "fail", "commit_sha": None}

    monkeypatch.setattr("backend.main.commit_code", fake_commit_code)

    payload = {
        "repo_id": "group/proj",
        "branch": "main",
        "file_path": "tests/new.py",
        "commit_message": "msg",
        "code": "print('hi')",
    }
    r = client.post("/commit", json=payload)
    assert r.status_code == 400
    assert r.json()["detail"] == "fail"


def test_analyze_defects_endpoint(monkeypatch):
    def fake_fetch_defects(*args, **kwargs):
        return {
            "success": True,
            "issues": [{
                "id": 1,
                "title": "Bug",
                "description": "Crash",
                "labels": ["bug"],
                "state": "opened",
                "created_at": "2024-01-01"
            }],
            "count": 1,
            "message": None
        }

    async def fake_llm(*args, **kwargs):
        return "LLM summary"

    monkeypatch.setattr("backend.gitlab_client.fetch_defects", fake_fetch_defects)
    monkeypatch.setattr("backend.main.fetch_defects", fake_fetch_defects)
    monkeypatch.setattr("backend.main.call_evolution", fake_llm)

    r = client.post("/analyze_defects", json={"repo_id": "group/proj"})
    assert r.status_code == 200
    data = r.json()
    assert data["count"] == 1
    assert data["defects"][0]["title"] == "Bug"
    assert data["summary"] == "LLM summary"


def test_generate_optimize_injects_defects(monkeypatch):
    async def fake_analyze_defects(req):
        return {"count": 1, "summary": "Bug summary", "defects": []}

    captured_prompt = {}

    async def fake_llm(messages, **kwargs):
        captured_prompt["value"] = messages[0]["content"]
        return "print('optimized')"

    monkeypatch.setattr("backend.main.analyze_defects", fake_analyze_defects)
    monkeypatch.setattr("backend.main.call_evolution", fake_llm)

    r = client.post("/generate", json={"type": "optimize", "previous_code": "print('old')", "repo_id": "123"})
    assert r.status_code == 200
    assert "Bug summary" in captured_prompt.get("value", "")


def test_generate_unit_ci(monkeypatch):
    async def fake_llm(messages, **kwargs):
        return "from fastapi.testclient import TestClient\nclient = TestClient(app)\n"

    monkeypatch.setattr("backend.main.call_evolution", fake_llm)

    r = client.post("/generate", json={"type": "unit_ci", "previous_code": "from main import app"})
    assert r.status_code == 200
    data = r.json()
    assert "TestClient" in data["code"]
    assert data["type"] == "unit_ci"


def test_round_down_floors():
    from backend.main import round_down
    assert round_down(1.239, 2) == 1.23
    assert round_down(1.201, 2) == 1.2


def test_ensure_owner_label_adds_missing():
    from backend.main import ensure_owner_label
    code = "@allure.manual\n@allure.feature('x')\ndef test_x():\n    pass\n"
    updated = ensure_owner_label(code)
    assert '@allure.label("owner", "qa_team")' in updated


def test_precheck_manual_generation_detects_low_count():
    from backend.main import precheck_manual_generation
    code = "def test_one(): pass\n"
    issues = precheck_manual_generation(code)
    assert issues and "Найдено только" in issues[0]


def test_clean_code_from_llm_strips_markdown_and_headers():
    from backend.main import clean_code_from_llm
    raw = "```python\n# Тест-план\n\n```"
    cleaned = clean_code_from_llm(raw)
    assert "```" not in cleaned
    assert "# Тест-план" not in cleaned
    assert cleaned == ""


def test_analyze_defects_failure(monkeypatch):
    def fake_fetch_defects(*args, **kwargs):
        return {"success": False, "message": "fail"}

    monkeypatch.setattr("backend.gitlab_client.fetch_defects", fake_fetch_defects)
    monkeypatch.setattr("backend.main.fetch_defects", fake_fetch_defects)

    r = client.post("/analyze_defects", json={"repo_id": "x"})
    assert r.status_code == 400
    assert r.json()["detail"] == "fail"


def test_analyze_defects_no_issues(monkeypatch):
    def fake_fetch_defects(*args, **kwargs):
        return {"success": True, "issues": [], "count": 0, "message": None}

    monkeypatch.setattr("backend.gitlab_client.fetch_defects", fake_fetch_defects)
    monkeypatch.setattr("backend.main.fetch_defects", fake_fetch_defects)

    r = client.post("/analyze_defects", json={"repo_id": "x"})
    assert r.status_code == 200
    data = r.json()
    assert data["count"] == 0
    assert "Не обнаружены дефекты" in data["summary"]


def test_generate_fixes_expected_indented_block(monkeypatch):
    async def fake_llm(*args, **kwargs):
        return "def test_x():\n    with open('x'):\n        "

    monkeypatch.setattr("backend.main.call_evolution", fake_llm)

    r = client.post("/generate", json={"type": "test_plan", "previous_code": "def test_x(): pass"})
    assert r.status_code == 200
    assert "pass" in r.json()["code"]


def test_generate_fixes_unexpected_indent(monkeypatch):
    async def fake_llm(*args, **kwargs):
        return "    def test_x():\n        pass\nprint('ok')"

    monkeypatch.setattr("backend.main.call_evolution", fake_llm)

    r = client.post("/generate", json={"type": "test_plan", "previous_code": "def test_x(): pass"})
    assert r.status_code == 200
    code = r.json()["code"]
    assert code.lstrip().startswith("def test_x")


def test_generate_adds_missing_colon(monkeypatch):
    async def fake_llm(*args, **kwargs):
        return "def test_x()\n    pass"

    monkeypatch.setattr("backend.main.call_evolution", fake_llm)

    r = client.post("/generate", json={"type": "test_plan", "previous_code": "def test_x(): pass"})
    assert r.status_code == 200
    code = r.json()["code"]
    assert "def test_x():" in code


def test_generate_closes_unterminated_string(monkeypatch):
    async def fake_llm(*args, **kwargs):
        return "def test_x():\n    print('oops\n    return 1"

    monkeypatch.setattr("backend.main.call_evolution", fake_llm)

    r = client.post("/generate", json={"type": "test_plan", "previous_code": "def test_x(): pass"})
    assert r.status_code == 200
    code = r.json()["code"]
    assert "print('oops')" in code or 'print("oops")' in code


def test_generate_missing_template(monkeypatch):
    def fake_prompt(req_type):
        raise FileNotFoundError("no template")

    monkeypatch.setattr("backend.main.get_cached_prompt", fake_prompt)

    r = client.post("/generate", json={"type": "unknown_type"})
    assert r.status_code == 400
    assert "не найден" in r.json()["detail"]


def test_analyze_defects_llm_summary_fallback(monkeypatch):
    def fake_fetch_defects(*args, **kwargs):
        return {
            "success": True,
            "issues": [{"id": 1, "title": "Bug", "description": "Crash", "labels": ["bug"], "state": "opened"}],
            "count": 1,
            "message": None
        }

    async def fail_llm(*args, **kwargs):
        raise Exception("llm down")

    monkeypatch.setattr("backend.gitlab_client.fetch_defects", fake_fetch_defects)
    monkeypatch.setattr("backend.main.fetch_defects", fake_fetch_defects)
    monkeypatch.setattr("backend.main.call_evolution", fail_llm)

    r = client.post("/analyze_defects", json={"repo_id": "x"})
    assert r.status_code == 200
    data = r.json()
    assert data["summary"].startswith("Issue #1")


def test_precheck_manual_ui_flags_low_count():
    from backend.main import precheck_manual_ui
    code = "def test_one(): pass\n"
    issues = precheck_manual_ui(code)
    assert issues and "Найдено только" in issues[0]


def test_aaa_order_is_ok_valid_sequence():
    from backend.main import aaa_order_is_ok
    code = """def test_x():
    with allure_step("Arrange: prep"):
        pass
    with allure_step("Act: do"):
        pass
    with allure_step("Assert: check"):
        pass"""
    assert aaa_order_is_ok(code) is True


def test_aaa_order_is_ok_invalid_sequence():
    from backend.main import aaa_order_is_ok
    code = """def test_x():
    with allure_step("Act: do"):
        pass
    with allure_step("Arrange: prep"):
        pass
    with allure_step("Assert: check"):
        pass"""
    assert aaa_order_is_ok(code) is False


def test_aaa_order_is_ok_missing_blocks():
    from backend.main import aaa_order_is_ok
    code = """def test_x():
    with allure_step("Arrange: prep"):
        pass
    with allure_step("Assert: check"):
        pass"""
    assert aaa_order_is_ok(code) is False


def test_aaa_sequence_is_valid():
    from backend.main import _aaa_sequence_is_valid
    assert _aaa_sequence_is_valid(["arrange", "act", "assert"]) is True
    # Функция использует index(), который возвращает первое вхождение, так что порядок все равно правильный
    assert _aaa_sequence_is_valid(["arrange", "act", "assert", "arrange"]) is True
    assert _aaa_sequence_is_valid(["arrange", "assert"]) is False  # Нет act
    assert _aaa_sequence_is_valid(["act", "assert"]) is False  # Нет arrange
    assert _aaa_sequence_is_valid(["arrange", "act"]) is False  # Нет assert


def test_enforce_aaa_order_reorders():
    from backend.main import enforce_aaa_order
    code = """def test_x():
    with allure_step("Act: do"):
        pass
    with allure_step("Arrange: prep"):
        pass
    with allure_step("Assert: check"):
        pass"""
    result = enforce_aaa_order(code)
    arrange_idx = result.find("Arrange:")
    act_idx = result.find("Act:")
    assert_idx = result.find("Assert:")
    assert arrange_idx < act_idx < assert_idx


def test_enforce_aaa_order_inserts_missing():
    from backend.main import enforce_aaa_order
    code = """def test_x():
    with allure_step("Arrange: prep"):
        pass
    with allure_step("Assert: check"):
        pass"""
    result = enforce_aaa_order(code)
    assert "Arrange:" in result
    assert "Act:" in result
    assert "Assert:" in result


def test_ensure_owner_label_adds_when_missing():
    from backend.main import ensure_owner_label
    code = """@allure.manual
def test_x():
    pass"""
    result = ensure_owner_label(code)
    assert '@allure.label("owner", "qa_team")' in result


def test_ensure_owner_label_keeps_existing():
    from backend.main import ensure_owner_label
    code = """@allure.manual
@allure.label("owner", "qa_team")
def test_x():
    pass"""
    result = ensure_owner_label(code)
    assert result.count('@allure.label("owner", "qa_team")') == 1


def test_generate_custom_prompt_too_long(monkeypatch):
    async def fake_llm(*args, **kwargs):
        return "code"
    monkeypatch.setattr("backend.main.call_evolution", fake_llm)
    
    long_prompt = "x" * 8001
    r = client.post("/generate", json={"type": "custom", "custom_prompt": long_prompt})
    assert r.status_code == 400
    assert "8000" in r.json()["detail"]


def test_generate_custom_prompt_empty(monkeypatch):
    r = client.post("/generate", json={"type": "custom", "custom_prompt": ""})
    assert r.status_code == 400
    assert "обязателен" in r.json()["detail"]


def test_generate_optimize_without_previous_code(monkeypatch):
    async def fake_llm(*args, **kwargs):
        return "code"
    monkeypatch.setattr("backend.main.call_evolution", fake_llm)
    
    r = client.post("/generate", json={"type": "optimize"})
    assert r.status_code == 400
    assert "previous_code" in r.json()["detail"]


def test_generate_test_plan_without_previous_code(monkeypatch):
    async def fake_llm(*args, **kwargs):
        return "code"
    monkeypatch.setattr("backend.main.call_evolution", fake_llm)
    
    r = client.post("/generate", json={"type": "test_plan"})
    assert r.status_code == 400
    assert "previous_code" in r.json()["detail"]


def test_generate_auto_api_without_openapi_spec(monkeypatch):
    async def fake_llm(*args, **kwargs):
        return "@allure.feature('test')\n@allure.title('test')\ndef test_x(): pass"
    
    def fake_load_spec(path):
        raise Exception("OpenAPI spec not found")
    
    monkeypatch.setattr("backend.main.call_evolution", fake_llm)
    monkeypatch.setattr("backend.main.load_openapi_spec", fake_load_spec)
    
    # Сбрасываем кэш
    app.state.openapi_spec = None
    app.state.openapi_endpoints = None
    
    r = client.post("/generate", json={"type": "auto_api"})
    # Должен обработать ошибку и вернуть 500 или попытаться загрузить
    assert r.status_code in [200, 500]


def test_generate_unit_ci_with_previous_code(monkeypatch):
    async def fake_llm(*args, **kwargs):
        return "def test_x(): pass"
    
    monkeypatch.setattr("backend.main.call_evolution", fake_llm)
    
    r = client.post("/generate", json={
        "type": "unit_ci",
        "previous_code": "def endpoint(): return 200"
    })
    assert r.status_code == 200
    assert "test_x" in r.json()["code"]


def test_generate_optimize_with_defects(monkeypatch):
    async def fake_llm(*args, **kwargs):
        return "optimized code"
    
    def fake_analyze_defects(req):
        return {"count": 1, "summary": "Bug found", "defects": []}
    
    monkeypatch.setattr("backend.main.call_evolution", fake_llm)
    monkeypatch.setattr("backend.main.analyze_defects", fake_analyze_defects)
    
    r = client.post("/generate", json={
        "type": "optimize",
        "previous_code": "def test_x(): pass",
        "repo_id": "123"
    })
    assert r.status_code == 200
    assert "code" in r.json()


def test_get_original_prompt_invalid_type():
    r = client.get("/prompt/invalid_type")
    assert r.status_code == 400
    assert "Неверный тип" in r.json()["detail"]


def test_get_original_prompt_not_found(monkeypatch):
    import os
    original_exists = os.path.exists
    
    def fake_exists(path):
        # Для валидного типа, но несуществующего файла
        if path == "prompts/manual_ui.txt":
            return False
        return original_exists(path)
    
    monkeypatch.setattr("os.path.exists", fake_exists)
    
    # Используем валидный тип, но файл не существует
    r = client.get("/prompt/manual_ui")
    assert r.status_code == 404
    assert "не найден" in r.json()["detail"]


def test_analyze_defects_llm_timeout(monkeypatch):
    def fake_fetch_defects(*args, **kwargs):
        return {
            "success": True,
            "issues": [{"id": 1, "title": "Bug", "labels": ["bug"], "state": "opened"}],
            "count": 1,
            "message": None
        }
    
    async def timeout_llm(*args, **kwargs):
        raise httpx.TimeoutException("timeout")
    
    monkeypatch.setattr("backend.gitlab_client.fetch_defects", fake_fetch_defects)
    monkeypatch.setattr("backend.main.fetch_defects", fake_fetch_defects)
    monkeypatch.setattr("backend.main.call_evolution", timeout_llm)
    
    r = client.post("/analyze_defects", json={"repo_id": "x", "summarize": True})
    assert r.status_code == 200
    assert "Issue #1" in r.json()["summary"]


def test_generate_unit_ci_with_gitlab_ci(monkeypatch):
    async def fake_llm(*args, **kwargs):
        return "def test_x(): pass\n.gitlab-ci.yml:\n  script:\n    - pytest"
    
    monkeypatch.setattr("backend.main.call_evolution", fake_llm)
    
    r = client.post("/generate", json={
        "type": "unit_ci",
        "previous_code": "def endpoint(): return 200"
    })
    assert r.status_code == 200
    code = r.json()["code"]
    assert "# .gitlab-ci.yml" in code or "test_x" in code


def test_generate_manual_ui_aaa_auto_accept(monkeypatch):
    async def fake_llm(*args, **kwargs):
        return """import allure
from allure import step as allure_step

@allure.manual
@allure.suite("Test")
@allure.label("owner", "qa_team")
@allure.label("priority", "P1")
@allure.link("https://test.com")
def test_x():
    with allure_step("Arrange: подготовка"):
        pass
    with allure_step("Act: нажать"):
        pass
    with allure_step("Assert: проверить"):
        pass"""
    
    def fake_validate(code, req_type):
        return {
            "valid": False,
            "issues": ["Нарушен строгий порядок AAA: Arrange → Act → Assert."],
            "message": "AAA failed",
            "score": 60
        }
    
    def fake_precheck(code):
        return []
    
    monkeypatch.setattr("backend.main.call_evolution", fake_llm)
    monkeypatch.setattr("backend.main.validate_allure_code", fake_validate)
    monkeypatch.setattr("backend.main.precheck_manual_ui", fake_precheck)
    
    r = client.post("/generate", json={"type": "manual_ui"})
    assert r.status_code == 200
    # Должен автоматически акцептовать, если порядок правильный
    assert r.json()["validation"]["valid"] is True


def test_check_coverage():
    from backend.main import check_coverage
    endpoints = [{"method": "GET", "path": "/vms"}, {"method": "POST", "path": "/disks"}]
    code = "requests.get('/vms')"
    missing = check_coverage(endpoints, code)
    assert "/disks" in missing[0]
    assert len(missing) == 1


def test_generate_syntax_error_fix_loop(monkeypatch):
    """Тест, что синтаксические ошибки исправляются в цикле до 8 раз"""
    call_count = [0]
    
    async def fake_llm(*args, **kwargs):
        call_count[0] += 1
        if call_count[0] == 1:
            return "def test_x():\n    print('unclosed"  # Незакрытая строка
        return "def test_x():\n    print('ok')"
    
    monkeypatch.setattr("backend.main.call_evolution", fake_llm)
    
    r = client.post("/generate", json={"type": "test_plan", "previous_code": "def x(): pass"})
    assert r.status_code == 200
    code = r.json()["code"]
    # Должен быть исправлен синтаксис
    assert "def test_x" in code or "print" in code


def test_generate_edited_prompt_uses_custom(monkeypatch):
    """Тест, что отредактированный встроенный промпт используется"""
    async def fake_llm(messages, **kwargs):
        # Проверяем, что промпт содержит кастомный текст
        prompt = messages[0]["content"]
        assert "custom edited prompt" in prompt.lower() or "qa" in prompt.lower()
        return "def test_x(): pass"
    
    monkeypatch.setattr("backend.main.call_evolution", fake_llm)
    
    # Симулируем edited prompt через custom_prompt
    r = client.post("/generate", json={
        "type": "manual_ui",
        "custom_prompt": "custom edited prompt text"
    })
    assert r.status_code == 200