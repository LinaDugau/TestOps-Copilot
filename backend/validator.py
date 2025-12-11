import ast
import re
from typing import List

def validate_allure_code(code: str, test_type: str = "manual_ui") -> dict:
    """
    Умная валидация:
    - manual_ui / manual_api → строгий Python + Allure TestOps as Code
    - auto_ui / auto_api → Python + @allure.feature + @allure.title
    - test_plan / optimize / any other → пропускаем валидацию (это не код)
    """
    if test_type in ["test_plan", "optimize", "optimization", "plan"]:
        return {
            "valid": True,
            "issues": [],
            "message": "Это не Python-код — валидация не требуется (тест-план/оптимизация)",
            "score": 100
        }

    issues = []

    try:
        ast.parse(code)
    except SyntaxError as e:
        error_msg = f"Синтаксическая ошибка Python: {e}"
        if e.lineno:
            error_msg += f" (строка {e.lineno})"
        if e.text:
            error_msg += f" в '{e.text.strip()}'"
        issues.append(error_msg)
        return {"valid": False, "issues": issues, "score": 0}

    if test_type in ["manual_ui", "manual_api"]:
        manual_required = [
            ("@allure.manual", r"@allure\s*\.\s*manual"),
            ("with allure_step(...)", r"with\s+allure_step\s*\("),
        ]
        missing = [label for label, pattern in manual_required if not re.search(pattern, code)]
        if missing:
            issues.append(f"Отсутствуют обязательные элементы для ручных тестов: {', '.join(missing)}")

        steps = re.findall(r'with\s+allure_step\s*\(\s*["\'](.+?)["\']\s*\)', code, flags=re.IGNORECASE)

        arrange = any(re.search(r"(подгот|открыт|перейти|setup|prepare)", s, re.IGNORECASE) for s in steps)
        act = any(re.search(r"(нажать|выбрать|создать|call|send|execute)", s, re.IGNORECASE) for s in steps)
        assert_ = any(re.search(r"(проверить|убедиться|assert|ожидать)", s, re.IGNORECASE) for s in steps)

        if not (arrange and act and assert_):
            issues.append(
                "Тест не соответствует AAA паттерну (Arrange–Act–Assert). "
                "Убедитесь, что есть шаги подготовки, действия и проверки."
            )

        # --- suite check ---
        if not re.search(r"@allure\.suite\s*\(", code):
            issues.append("Отсутствует обязательный @allure.suite(...)")

        # --- link check ---
        if not re.search(r"@allure\.link\s*\(\s*['\"]https?://", code):
            issues.append("Рекомендуется добавить @allure.link(...) на документацию или Jira-задачу")

        # --- priority check ---
        priority_match = re.search(r'@allure\.label\(\s*[\'"]priority[\'"]\s*,\s*[\'"](.+?)[\'"]\s*\)', code)

        if not priority_match:
            issues.append("Отсутствует метка @allure.label('priority', '...'). Допустимые значения: HIGH/MEDIUM/LOW или P1–P5.")
        else:
            priority = priority_match.group(1).upper()
            allowed = {"HIGH", "MEDIUM", "LOW", "P1", "P2", "P3", "P4", "P5"}
            if priority not in allowed:
                issues.append(f"Недопустимый priority '{priority}'. Допустимые значения: {', '.join(allowed)}")

        # --- owner label strict check ---
        owner_match = re.search(r'@allure\.label\(\s*[\'"]owner[\'"]\s*,\s*[\'"](.+?)[\'"]\s*\)', code)
        if owner_match:
            owner_value = owner_match.group(1)
            valid_owner = re.match(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9.-]+$|^qa_[a-z]+$|^[A-Z][a-z]+ [A-Z][a-z]+$", owner_value)
            if not valid_owner:
                issues.append(
                    "Неверный формат owner. Используйте email, формат 'qa_team' или 'Имя Фамилия'."
                )
        else:
            issues.append("Отсутствует обязательный owner (@allure.label('owner', ...)).")

    elif test_type in ["auto_ui", "auto_api"]:
        if "@allure.feature" not in code or "@allure.title" in code:
            pass  
        else:
            issues.append("Рекомендуется использовать @allure.feature и @allure.title")

    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "message": "Валидация пройдена" if not issues else f"Найдено {len(issues)} проблем",
        "score": 100 if not issues else max(40, 100 - 20 * len(issues))
    }


def extract_api_calls(code: str) -> List[str]:
    """
    Parse code for API calls (requests.get/post/etc.) and return unique endpoints.
    Handles string literals and simple f-strings; ignores malformed code gracefully.
    """
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return []

    endpoints: list[str] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            func_attr = node.func.attr
            value = node.func.value

            is_requests_call = (
                func_attr in ["get", "post", "put", "delete"]
                and isinstance(value, ast.Name)
                and value.id == "requests"
            )
            if not is_requests_call:
                continue

            if node.args:
                first_arg = node.args[0]
                if isinstance(first_arg, (ast.Str, ast.Constant)) and isinstance(getattr(first_arg, "value", None), str):
                    endpoints.append(first_arg.value)
                elif isinstance(first_arg, ast.JoinedStr):  # f-string
                    parts = [p.value for p in first_arg.values if isinstance(p, ast.Constant) and isinstance(p.value, str)]
                    if parts:
                        endpoints.append(parts[0])

    unique_endpoints = {ep for ep in endpoints if isinstance(ep, str) and ep.startswith(("/", "http"))}
    return list(unique_endpoints)