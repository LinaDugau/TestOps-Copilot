import ast
import re
from typing import List


def validate_allure_code(code: str, test_type: str = "manual_ui") -> dict:
    """
    Улучшенная строгая валидация Allure-кода:
    - manual_ui / manual_api → обязателен Allure TestOps формат + AAA паттерн + suite/link/priority/owner
    - auto_ui / auto_api → мягкая проверка feature/title
    - test_plan / optimize → валидация отключена
    """

    # --------------------------------------------------------
    # 0. Не валидируем тест-планы и оптимизацию (это не Python)
    # --------------------------------------------------------
    if test_type in ["test_plan", "optimize", "optimization", "plan"]:
        return {
            "valid": True,
            "issues": [],
            "message": "Валидация не требуется (test_plan/optimize)",
            "score": 100
        }

    issues = []

    # --------------------------------------------------------
    # 1. Проверка на синтаксис Python
    # --------------------------------------------------------
    try:
        ast.parse(code)
    except SyntaxError as e:
        msg = f"Синтаксическая ошибка Python: {e}"
        if e.lineno:
            msg += f" (строка {e.lineno})"
        if e.text:
            msg += f" → '{e.text.strip()}'"
        issues.append(msg)
        return {"valid": False, "issues": issues, "score": 0}

    # ===================================================================
    # 2. Валидация ручных тестов (самая строгая часть)
    # ===================================================================
    if test_type in ["manual_ui", "manual_api"]:

        # -------------------------------
        # 2.1 Проверка обязательных элементов
        # -------------------------------
        required = [
            ("@allure.manual", r"@allure\s*\.\s*manual"),
            ("with allure_step(...)", r"with\s+allure_step\s*\("),
        ]

        missing = [name for name, pattern in required if not re.search(pattern, code)]
        if missing:
            issues.append(
                "Отсутствуют обязательные элементы: " + ", ".join(missing)
            )

        # -------------------------------
        # 2.2 Извлечение allure_step для AAA-валидации
        # -------------------------------
        steps = re.findall(
            r'with\s+allure_step\s*\(\s*["\'](.+?)["\']\s*\)',
            code,
            flags=re.IGNORECASE
        )

        # -------------------------------
        # 2.3 Строгий AAA порядок
        # -------------------------------
        aaa_order = []

        for s in steps:
            s_lower = s.lower()

            # MATCH ARRANGE
            if re.search(r"(подгот|setup|prepare|открыт|перейти|init|login)", s_lower):
                aaa_order.append("A1")

            # MATCH ACT
            elif re.search(r"(нажать|клик|выбрать|создать|call|send|execute|submit)", s_lower):
                aaa_order.append("A2")

            # MATCH ASSERT
            elif re.search(r"(проверить|assert|validate|ожидать|убедиться)", s_lower):
                aaa_order.append("A3")

        # now validate strict monotonic sequence A1 → A2 → A3
        seen_A1, seen_A2, seen_A3 = False, False, False
        order_error = False

        for token in aaa_order:
            if token == "A1":
                if seen_A2 or seen_A3:
                    order_error = True
                    break
                seen_A1 = True

            elif token == "A2":
                if not seen_A1 or seen_A3:
                    order_error = True
                    break
                seen_A2 = True

            elif token == "A3":
                if not seen_A2:
                    order_error = True
                    break
                seen_A3 = True

        # финальное решение AAA-блока
        if order_error or not (seen_A1 and seen_A2 and seen_A3):
            issues.append(
                "Нарушен строгий порядок AAA: Arrange → Act → Assert. "
                "Убедитесь, что шаги идут последовательно."
            )

        # -------------------------------
        # 2.4 @allure.suite обязательный
        # -------------------------------
        if not re.search(r"@allure\.suite\s*\(", code):
            issues.append("Отсутствует обязательный @allure.suite(...).")

        # -------------------------------
        # 2.5 @allure.link (Jira / документация)
        # -------------------------------
        if not re.search(r"@allure\.link\s*\(\s*['\"]https?://", code):
            issues.append(
                "Рекомендуется добавить @allure.link('https://jira...') "
                "для связи теста с требованиями."
            )

        # -------------------------------
        # 2.6 priority label
        # -------------------------------
        p = re.search(
            r"@allure\.label\(\s*['\"]priority['\"]\s*,\s*['\"](.+?)['\"]\s*\)",
            code
        )

        allowed = {"HIGH", "MEDIUM", "LOW", "P1", "P2", "P3", "P4", "P5"}

        if not p:
            issues.append(
                "Отсутствует @allure.label('priority', ...). "
                f"Допустимые значения: {', '.join(allowed)}"
            )
        else:
            pr = p.group(1).upper()
            if pr not in allowed:
                issues.append(
                    f"Недопустимый priority '{pr}'. "
                    f"Разрешено: {', '.join(allowed)}"
                )

        # -------------------------------
        # 2.7 owner label strict
        # -------------------------------
        o = re.search(
            r"@allure\.label\(\s*['\"]owner['\"]\s*,\s*['\"](.+?)['\"]\s*\)",
            code
        )

        if not o:
            issues.append("Отсутствует обязательный @allure.label('owner', ...).")
        else:
            owner_val = o.group(1)
            valid_owner = re.match(
                r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9.-]+$"          # email
                r"|^qa_[a-z]+$"                               # qa_team
                r"|^[A-Z][a-z]+ [A-Z][a-z]+$",                # Имя Фамилия
                owner_val
            )
            if not valid_owner:
                issues.append(
                    "Неверный формат owner. Допустимо: email, 'qa_team', 'Имя Фамилия'"
                )

    # ===================================================================
    # 3. Автоматические тесты — мягкая валидация
    # ===================================================================
    elif test_type in ["auto_ui", "auto_api"]:
        if "@allure.feature" not in code:
            issues.append("Рекомендуется использовать @allure.feature(...)")
        if "@allure.title" not in code:
            issues.append("Рекомендуется использовать @allure.title(...)")

    # ===================================================================
    # Финальный ответ
    # ===================================================================
    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "message": "Валидация пройдена" if not issues else f"Найдено {len(issues)} проблем",
        "score": 100 if not issues else max(40, 100 - 10 * len(issues))
    }


# ===================================================================
# Вспомогательная функция извлечения API вызовов
# ===================================================================
def extract_api_calls(code: str) -> List[str]:
    """
    Parse code for API calls (requests.get/post/etc.) and return unique endpoints.
    Handles string literals and simple f-strings; ignores malformed code gracefully.
    """
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return []

    endpoints: List[str] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr in ["get", "post", "put", "delete"]:
                if isinstance(node.func.value, ast.Name) and node.func.value.id == "requests":

                    if node.args:
                        arg = node.args[0]

                        if isinstance(arg, (ast.Str, ast.Constant)) and isinstance(arg.value, str):
                            endpoints.append(arg.value)

                        elif isinstance(arg, ast.JoinedStr):  # f-string
                            const_parts = [
                                p.value for p in arg.values
                                if isinstance(p, ast.Constant) and isinstance(p.value, str)
                            ]
                            if const_parts:
                                endpoints.append(const_parts[0])

    return list({ep for ep in endpoints if ep.startswith(("/", "http"))})