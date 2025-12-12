from backend.validator import validate_allure_code, extract_api_calls

def test_validator_accepts_valid_manual_ui():
    code = (
        "import allure\n"
        "from allure import step as allure_step\n"
        "@allure.manual\n"
        "@allure.suite(\"Test Suite\")\n"
        "@allure.label(\"owner\", \"qa_team\")\n"
        "@allure.label(\"priority\", \"P1\")\n"
        "@allure.link(\"https://jira.example.com\")\n"
        "class T:\n"
        "    def x(self):\n"
        "        with allure_step(\"Arrange: подготовка данных\"):\n"
        "            pass\n"
        "        with allure_step(\"Act: нажать кнопку\"):\n"
        "            pass\n"
        "        with allure_step(\"Assert: проверить результат\"):\n"
        "            pass\n"
    )
    result = validate_allure_code(code, "manual_ui")
    assert result["valid"] is True
    assert result["issues"] == []

def test_validator_accepts_owner_single_quotes():
    code = (
        "import allure\n"
        "from allure import step as allure_step\n"
        "@allure.manual\n"
        "@allure.suite('Test Suite')\n"
        "@allure.label('owner', 'qa_team')\n"
        "@allure.label('priority', 'P1')\n"
        "@allure.link('https://jira.example.com')\n"
        "def test_single_quotes_owner():\n"
        "    with allure_step('Arrange: подготовка данных'):\n"
        "        pass\n"
        "    with allure_step('Act: нажать кнопку'):\n"
        "        pass\n"
        "    with allure_step('Assert: проверить результат'):\n"
        "        pass\n"
    )
    result = validate_allure_code(code, "manual_api")
    assert result["valid"] is True
    assert result["issues"] == []


def test_validator_detects_missing_required_elements():
    code = "def test_x(): pass"
    result = validate_allure_code(code, "manual_api")
    assert result["valid"] is False
    assert "Отсутствуют обязательные элементы" in result["issues"][0]


def test_validator_parses_invalid_python():
    code = "def test(:"
    result = validate_allure_code(code, "manual_ui")
    assert result["valid"] is False
    assert "Синтаксическая ошибка Python" in result["issues"][0]


def test_validator_accepts_new_tags_free_tier():
    code = '''
import allure
from allure import step as allure_step
@allure.manual
@allure.suite("Калькулятор цен Cloud.ru")
@allure.label("owner", "qa_team")
@allure.label("priority", "P1")
@allure.link("https://cloud.ru/price-calculator")
@allure.feature("Калькулятор цен Cloud.ru")
@allure.story("ConfigurationManagementTests")
class ConfigurationManagementTests:
    @allure.title("Добавление Free Tier продукта")
    @allure.tag("HIGH")
    def test_add_free_tier_success(self) -> None:
        with allure_step("Arrange: Открыть каталог продуктов"):
            pass
        with allure_step("Act: Выбрать Free Tier вариант Compute"):
            pass
        with allure_step("Assert: Проверить добавление без стоимости"):
            pass
    '''
    result = validate_allure_code(code, "manual_ui")
    assert result["valid"] is True
    assert "Free Tier" in code
    assert result["issues"] == []


def test_validator_skips_test_plan():
    result = validate_allure_code("steps only", "test_plan")
    assert result["valid"] is True
    assert "Валидация не требуется" in result["message"] or "test_plan" in result["message"]


def test_validator_warns_auto_missing_title():
    code = (
        "@allure.feature('X')\n"
        "def test_y():\n"
        "    pass\n"
    )
    result = validate_allure_code(code, "auto_api")
    assert result["valid"] is False
    assert "рекомендуется".lower() in result["issues"][0].lower()


def test_extract_api_calls_simple():
    code = 'import requests\nrequests.get("/vms")\nrequests.post("/disks")\n'
    endpoints = extract_api_calls(code)
    assert set(endpoints) == {"/vms", "/disks"}


def test_extract_api_calls_invalid_code_returns_empty():
    endpoints = extract_api_calls("def nope(:")  # SyntaxError inside parser
    assert endpoints == []


def test_extract_api_calls_fstring_keeps_literal_prefix():
    code = 'import requests\nbase = "http://api"\nrequests.get(f"{base}/vms/{id}")\n'
    endpoints = extract_api_calls(code)
    assert endpoints == ["/vms/"]


def test_extract_api_calls_ignores_non_requests_calls():
    code = "import httpx\nhttpx.get('http://x')\n"
    assert extract_api_calls(code) == []


def test_extract_api_calls_without_args():
    code = "import requests\nrequests.get()\n"
    assert extract_api_calls(code) == []


def test_validator_auto_api_ok_with_title_and_feature():
    code = (
        "@allure.feature('X')\n"
        "@allure.title('Y')\n"
        "def test_y():\n"
        "    pass\n"
    )
    result = validate_allure_code(code, "auto_api")
    assert result["valid"] is True
    assert result["issues"] == []