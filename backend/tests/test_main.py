import asyncio
import time
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_root_endpoint():
    r = client.get("/")
    assert r.status_code == 200
    assert "TestOps Copilot" in r.json()["message"]


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


def test_generate_auto_api_recovers_from_annotation_error(monkeypatch):
    async def fake_llm(*args, **kwargs):
        return '"project_id": "project-uuid",\nprint("still works")'

    monkeypatch.setattr("backend.main.call_evolution", fake_llm)

    r = client.post("/generate", json={"type": "auto_api"})
    assert r.status_code == 200
    data = r.json()
    assert data["validation"]["valid"] is True
    assert '"project_id": "project-uuid"' not in data["code"]
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
    broken_code = 'def test_x():\n    print("hello'  

    async def fake_llm(*args, **kwargs):
        return broken_code 

    monkeypatch.setattr("backend.main.call_evolution", fake_llm)

    r = client.post("/generate", json={"type": "auto_api"})
    assert r.status_code == 200
    data = r.json()
    assert data["validation"]["valid"] is True  # После fix ast.parse OK
    assert '"hello"' in data["code"]  # Fix закрыл кавычку
    assert "print(\"hello\")" in data["code"]  # Или аналогичный fix


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

    r = client.post("/generate", json={"type": "test_plan"})
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
    from backend.main import analyze_defects

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

    r = client.post("/generate", json={"type": "test_plan"})
    assert r.status_code == 200
    assert "pass" in r.json()["code"]


def test_generate_fixes_unexpected_indent(monkeypatch):
    async def fake_llm(*args, **kwargs):
        return "    def test_x():\n        pass\nprint('ok')"

    monkeypatch.setattr("backend.main.call_evolution", fake_llm)

    r = client.post("/generate", json={"type": "test_plan"})
    assert r.status_code == 200
    code = r.json()["code"]
    assert code.lstrip().startswith("def test_x")


def test_generate_adds_missing_colon(monkeypatch):
    async def fake_llm(*args, **kwargs):
        return "def test_x()\n    pass"

    monkeypatch.setattr("backend.main.call_evolution", fake_llm)

    r = client.post("/generate", json={"type": "test_plan"})
    assert r.status_code == 200
    code = r.json()["code"]
    assert "def test_x():" in code


def test_generate_closes_unterminated_string(monkeypatch):
    async def fake_llm(*args, **kwargs):
        return "def test_x():\n    print('oops\n    return 1"

    monkeypatch.setattr("backend.main.call_evolution", fake_llm)

    r = client.post("/generate", json={"type": "test_plan"})
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