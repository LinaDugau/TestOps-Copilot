import pytest

from backend.main import clean_code_from_llm


def test_clean_code_removes_markdown_fences():
    raw = "```python\nprint('hi')\n```"
    cleaned = clean_code_from_llm(raw)
    assert cleaned == "print('hi')"


def test_clean_code_removes_trash_prefixes():
    raw = "Вот результат:\nprint('ok')"
    cleaned = clean_code_from_llm(raw)
    assert cleaned == "print('ok')"


def test_clean_code_closes_unterminated_double_quotes():
    raw = 'print("hello'
    cleaned = clean_code_from_llm(raw)
    assert cleaned.endswith('"')
    assert 'print("hello"' in cleaned


def test_clean_code_closes_unterminated_single_quotes():
    raw = "print('hello"
    cleaned = clean_code_from_llm(raw)
    assert cleaned.endswith("'")
    assert "print('hello'" in cleaned


def test_clean_code_removes_last_broken_short_string():
    raw = 'print("hello")\n"'
    cleaned = clean_code_from_llm(raw)
    assert cleaned == 'print("hello")'


def test_clean_code_keeps_comments():
    raw = "# comment\nprint('x')"
    cleaned = clean_code_from_llm(raw)
    assert cleaned == "# comment\nprint('x')"


def test_clean_code_does_not_modify_valid_code():
    raw = "a = 1\nb = 2\nprint(a+b)"
    cleaned = clean_code_from_llm(raw)
    assert cleaned == raw

def test_clean_code_adds_missing_owner_label():
    raw = '''
import allure
from allure import step as allure_step

@allure.manual
@allure.feature("Test")
class ExampleTests:
    @allure.title("Test without owner")
    def test_something(self):
        with allure_step("step"):
            pass
'''
    from backend.main import ensure_owner_label
    fixed = ensure_owner_label(raw)
    assert '@allure.label("owner", "qa_team")' in fixed
    assert fixed.count('@allure.label("owner", "qa_team")') == 1


def test_clean_code_preserves_existing_owner_label():
    raw = '''
import allure
from allure import step as allure_step

@allure.manual
@allure.label("owner", "qa_team")
@allure.feature("Test")
class ExampleTests:
    def test_ok(self):
        with allure_step("step"):
            pass
'''
    from backend.main import ensure_owner_label
    fixed = ensure_owner_label(raw)
    assert fixed.count('@allure.label("owner", "qa_team")') == 1 


def test_clean_code_handles_multiple_manual_classes():
    raw = '''
@allure.manual
class First:
    def test_a(self): pass

@allure.manual
class Second:
    def test_b(self): pass
'''
    from backend.main import ensure_owner_label
    fixed = ensure_owner_label(raw)
    owner_lines = [line for line in fixed.splitlines() if 'owner' in line]
    assert len(owner_lines) == 2
    assert all('"qa_team"' in line for line in owner_lines)

def test_clean_code_fixes_unterminated_multiline_string_at_end():
    raw = '''
print("Hello
world)
'''
    from backend.main import clean_code_from_llm
    cleaned = clean_code_from_llm(raw)
    assert cleaned == 'print("Hello world")'


def test_clean_code_removes_trailing_broken_quote_line():
    raw = '''
def test_x():
    assert True
"
'''
    from backend.main import clean_code_from_llm
    cleaned = clean_code_from_llm(raw)
    assert cleaned.strip() == 'def test_x():\n    assert True'

def test_clean_code_removes_optimize_header():
    raw = "### ОПТИМИЗИРОВАННЫЙ НАБОР ТЕСТ-КЕЙСОВ:\nimport allure\n\ndef test_x(): pass"
    cleaned = clean_code_from_llm(raw)
    assert cleaned == "import allure\n\ndef test_x(): pass"


def test_clean_code_removes_test_plan_header():
    raw = "# Тест-план для Evolution Compute API\n\n```python\nimport pytest\n```"
    cleaned = clean_code_from_llm(raw)
    assert cleaned == "import pytest"


def test_clean_code_fixes_unclosed_multiline_string():
    raw = 'allure.title("Тест с очень длинным названием, которое не влезает в одну строку и обрывается'
    cleaned = clean_code_from_llm(raw)
    assert cleaned.endswith('"')
    assert cleaned.count('"') % 2 == 0


def test_clean_code_removes_last_broken_line():
    raw = 'def test_ok():\n    assert True\nprint("'
    cleaned = clean_code_from_llm(raw)
    assert cleaned == "def test_ok():\n    assert True"


def test_clean_code_handles_escaped_quotes():
    raw = 'print("hello \\"world")'
    cleaned = clean_code_from_llm(raw)
    assert cleaned == raw


def test_clean_code_merges_lines_for_unclosed_string():
    raw = 'print("hello\nworld")'
    cleaned = clean_code_from_llm(raw)
    assert cleaned == 'print("hello world")'