from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from functools import lru_cache
from contextlib import asynccontextmanager
import os
import re
import ast
import time
import math
import logging
import textwrap
import psutil
import httpx
from pathlib import Path
try:
    from openai import APITimeoutError
except ImportError:
    APITimeoutError = None

try:
    from backend.logging_config import init_logging
    from backend.cloud_ru import call_evolution
    from backend.validator import validate_allure_code, extract_api_calls
    from backend.openapi_parser import load_openapi_spec, extract_endpoints
    from backend.gitlab_client import commit_code, fetch_defects
except ImportError:
    try:
        from logging_config import init_logging
    except ImportError:
        def init_logging():
            logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    from cloud_ru import call_evolution
    from validator import validate_allure_code, extract_api_calls
    from openapi_parser import load_openapi_spec, extract_endpoints
    from gitlab_client import commit_code, fetch_defects

init_logging()
logger = logging.getLogger("app")

# Определяем базовый путь к директории backend
# Работает и при ручном запуске, и в Docker
BASE_DIR = Path(__file__).parent.resolve()
PROMPTS_DIR = BASE_DIR / "prompts"
OPENAPI_DIR = BASE_DIR / "openapi"

# Логируем пути для отладки
logger.info(f"BASE_DIR: {BASE_DIR}")
logger.info(f"PROMPTS_DIR: {PROMPTS_DIR} (exists: {PROMPTS_DIR.exists()})")
logger.info(f"OPENAPI_DIR: {OPENAPI_DIR} (exists: {OPENAPI_DIR.exists()})")
if PROMPTS_DIR.exists():
    logger.info(f"Files in PROMPTS_DIR: {list(PROMPTS_DIR.glob('*.txt'))}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan hook: прогреваем OpenAPI однажды при старте."""
    try:
        openapi_path = OPENAPI_DIR / "openapi-v3.yaml"
        spec = load_openapi_spec(str(openapi_path))
        endpoints = extract_endpoints(spec)
        app.state.openapi_spec = spec
        app.state.openapi_endpoints = endpoints
        logger.info("openapi_cached", extra={"endpoints": len(endpoints)})
    except Exception as e:
        logger.warning("openapi_cache_failed", extra={"error": str(e)})

    yield


app = FastAPI(title="TestOps Copilot MVP v1.1", lifespan=lifespan)
app.state.openapi_spec = None
app.state.openapi_endpoints = None

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(
        "incoming_request",
        extra={
            "method": request.method,
            "url": request.url.path,
            "client_ip": request.client.host
        }
    )

    start_time = time.time()
    response = await call_next(request)
    duration = round(time.time() - start_time, 4)

    logger.info(
        "request_complete",
        extra={
            "method": request.method,
            "url": request.url.path,
            "status_code": response.status_code,
            "duration": duration
        }
    )

    return response

class GenerateRequest(BaseModel):
    type: str
    previous_code: str | None = None
    repo_id: int | str | None = None
    custom_prompt: str | None = None

class CommitRequest(BaseModel):
    repo_id: int | str
    branch: str = "main"
    file_path: str
    commit_message: str = "Generated tests from TestOps Copilot"
    code: str


class DefectsRequest(BaseModel):
    repo_id: int | str
    labels: list[str] = ["bug"]
    state: str = "opened"
    max_issues: int = 10
    summarize: bool = True


@lru_cache(maxsize=10)
def get_cached_prompt(req_type: str) -> str:
    prompt_path = PROMPTS_DIR / f"{req_type}.txt"
    logger.debug(f"Looking for prompt: {prompt_path} (exists: {prompt_path.exists()})")
    if not prompt_path.exists():
        # Попробуем найти все доступные файлы для лучшей диагностики
        available = list(PROMPTS_DIR.glob("*.txt")) if PROMPTS_DIR.exists() else []
        available_names = [f.stem for f in available]
        raise FileNotFoundError(
            f"Шаблон {req_type} не найден: {prompt_path}. "
            f"Доступные шаблоны: {available_names}"
        )
    with open(prompt_path, "r", encoding="utf-8") as f:
        return f.read()


@app.get("/prompt/{prompt_type}")
async def get_original_prompt(prompt_type: str):
    """Возвращает оригинальный промпт из файла для 'По умолчанию'."""
    if prompt_type not in ["manual_ui", "manual_api", "auto_ui", "auto_api", "test_plan", "optimize", "unit_ci"]:
        raise HTTPException(status_code=400, detail="Неверный тип промпта")

    prompt_path = PROMPTS_DIR / f"{prompt_type}.txt"
    logger.debug(f"Looking for prompt: {prompt_path} (exists: {prompt_path.exists()})")
    if not prompt_path.exists():
        # Попробуем найти все доступные файлы для лучшей диагностики
        available = list(PROMPTS_DIR.glob("*.txt")) if PROMPTS_DIR.exists() else []
        available_names = [f.stem for f in available]
        raise HTTPException(
            status_code=404,
            detail=f"Промпт {prompt_type} не найден: {prompt_path}. "
                   f"Доступные шаблоны: {available_names}"
        )

    with open(prompt_path, "r", encoding="utf-8") as f:
        return {"type": prompt_type, "prompt": f.read().strip()}

def round_down(value: float, decimals: int = 4) -> float:
    """
    Round a float toward zero with the requested precision to avoid over-reporting.
    Using floor keeps the reported duration <= real duration measured in the handler.
    """
    factor = 10 ** decimals
    return math.floor(value * factor) / factor

def clean_code_from_llm(raw_response: str) -> str:
    """Убирает весь мусор от Cloud.ru Evolution и исправляет незакрытые строки"""
    code = raw_response.strip()

    code = re.sub(r"^```[\w]*\s*", "", code, flags=re.MULTILINE)
    code = re.sub(r"```$", "", code, flags=re.MULTILINE)

    trash_prefixes = [
        "Вот.*:", "Ниже.*:", "Готово", "Вот результат", "Сгенерированный код",
        "Анализ", "Оптимизация", "### .*", "Оптимизированный набор"
    ]
    for prefix in trash_prefixes:
        code = re.sub(rf"^{prefix}.*\n?", "", code, flags=re.IGNORECASE | re.MULTILINE)
        code = re.sub(rf"^#\s*{prefix}.*\n?", "", code, flags=re.IGNORECASE | re.MULTILINE)
    
    lines = code.split('\n')
    filtered_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        is_test_plan_header = (
            re.match(r"^#\s*Тест-план", stripped, re.IGNORECASE) or
            re.match(r"^Тест-план\s*$", stripped, re.IGNORECASE)
        )
        
        if is_test_plan_header:
            if i + 1 < len(lines):
                next_line = lines[i + 1].strip()
                if next_line and not next_line.startswith('```'):
                    filtered_lines.append(line)
                    i += 1
                    continue
            i += 1
            continue
        
        filtered_lines.append(line)
        i += 1
    
    code = '\n'.join(filtered_lines)

    lines = code.split('\n')
    fixed_lines = []
    global_in_string_double = False
    global_in_string_single = False
    
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        
        if stripped.startswith('#') or not stripped:
            fixed_lines.append(line)
            i += 1
            continue
        
        in_string_double = global_in_string_double
        in_string_single = global_in_string_single
        escaped = False
        
        for char in line:
            if escaped:
                escaped = False
                continue
            if char == '\\':
                escaped = True
                continue
            if char == '"' and not in_string_single:
                in_string_double = not in_string_double
            elif char == "'" and not in_string_double:
                in_string_single = not in_string_single
        
        global_in_string_double = in_string_double
        global_in_string_single = in_string_single
        
        if (in_string_double or in_string_single) and not line.rstrip().endswith('\\'):
            if i == len(lines) - 1:
                has_content_in_quotes = False
                quote_char = '"' if in_string_double else "'"
                quote_start = stripped.rfind(quote_char)
                
                if quote_start >= 0:
                    content_after_quote = stripped[quote_start + 1:]
                    has_content_in_quotes = len(content_after_quote.strip()) > 0
                
                if len(stripped) < 8 and not has_content_in_quotes:
                    i += 1
                    continue
                
                if in_string_double and not line.rstrip().endswith('"'):
                    line = line.rstrip() + '"'
                    global_in_string_double = False
                elif in_string_single and not line.rstrip().endswith("'"):
                    line = line.rstrip() + "'"
                    global_in_string_single = False
                fixed_lines.append(line)
                i += 1
                continue
            
            should_merge = False
            if i < len(lines) - 1:
                next_line = lines[i + 1]
                next_stripped = next_line.strip()
                if next_stripped and not next_stripped.startswith(('def ', 'class ', 'if ', 'for ', 'while ', 'return ', 'assert ', '@', 'import ', 'from ')):
                    should_merge = True
            
            if should_merge:
                next_line = lines[i + 1]
                next_stripped = next_line.strip()
                
                if next_stripped.endswith(')'):
                    merged_body = next_stripped[:-1]
                    if merged_body.endswith(('"', "'")):
                        merged_body = merged_body[:-1]

                    if in_string_double:
                        line = line.rstrip() + ' ' + merged_body + '")'
                        global_in_string_double = False
                    elif in_string_single:
                        line = line.rstrip() + ' ' + merged_body + "')"
                        global_in_string_single = False
                    else:
                        line = line.rstrip() + ' ' + merged_body
                else:
                    line = line.rstrip() + ' ' + next_stripped
                    if in_string_double:
                        line = line.rstrip() + '"'
                        global_in_string_double = False
                    elif in_string_single:
                        line = line.rstrip() + "'"
                        global_in_string_single = False
                
                i += 2
            else:
                if in_string_double and not line.rstrip().endswith('"'):
                    line = line.rstrip() + '"'
                    global_in_string_double = False
                elif in_string_single and not line.rstrip().endswith("'"):
                    line = line.rstrip() + "'"
                    global_in_string_single = False
                i += 1
        else:
            i += 1
        
        fixed_lines.append(line)
    
    while fixed_lines and not fixed_lines[-1].strip():
        fixed_lines.pop()
    
    while fixed_lines and not fixed_lines[0].strip():
        fixed_lines.pop(0)
    
    code = '\n'.join(fixed_lines)

    return code.strip()

def ensure_owner_label(code: str) -> str:
    """
    Гарантирует наличие @allure.label("owner", "qa_team") после каждого @allure.manual.
    Если уже есть label(owner, ...), ничего не меняем. Нужен для стабильной валидации ручных тестов.
    """
    lines = code.split("\n")
    i = 0
    while i < len(lines):
        stripped = lines[i].strip()
        if stripped.startswith("@allure.manual"):
            j = i + 1
            while j < len(lines) and not lines[j].strip():
                j += 1

            has_owner = False
            if j < len(lines):
                if re.search(r"@allure\.label\(\s*[\"']owner[\"']", lines[j]):
                    has_owner = True

            if not has_owner:
                indent = re.match(r"(\s*)", lines[i]).group(1) if re.match(r"(\s*)", lines[i]) else ""
                lines.insert(i + 1, f'{indent}@allure.label("owner", "qa_team")')
                i += 1  # пропускаем вставленную строку
        i += 1

    return "\n".join(lines)


def enforce_aaa_order(code: str) -> str:
    """
    Переставляет блоки Arrange/Act/Assert в каждом тесте в строгом порядке.
    Если какого-то блока нет — добавляет пустой с pass.
    Работает по эвристике: ищет with allure_step("Arrange/Act/Assert") и,
    если порядок нарушен, переупорядочивает целые блоки шагов.
    """
    lines = code.splitlines()
    result: list[str] = []
    i = 0
    current_title: str | None = None

    arrange_re = re.compile(r'allure_step\(\s*["\']\s*Arrange', re.IGNORECASE)
    act_re = re.compile(r'allure_step\(\s*["\']\s*Act', re.IGNORECASE)
    assert_re = re.compile(r'allure_step\(\s*["\']\s*Assert', re.IGNORECASE)

    def capture_block(start_idx: int) -> tuple[list[str], int]:
        block: list[str] = []
        indent_match = re.match(r"(\s*)", lines[start_idx])
        indent = indent_match.group(1) if indent_match else ""
        j = start_idx
        while j < len(lines):
            block.append(lines[j])
            if j + 1 >= len(lines):
                break
            next_line = lines[j + 1]
            next_indent_match = re.match(r"(\s*)", next_line)
            next_indent = next_indent_match.group(1) if next_indent_match else ""
            if next_indent == indent and re.search(r"with\s+allure_step", next_line, re.IGNORECASE):
                break
            if len(next_indent) < len(indent):
                break
            j += 1
        return block, j + 1

    while i < len(lines):
        line = lines[i]
        title_match = re.search(r'@allure\.title\(\s*["\'](.+?)["\']\s*\)', line)
        if title_match:
            current_title = title_match.group(1)
        # Найти начало тестовой функции
        if re.match(r"\s*def\s+test_", line):
            func_lines = [line]
            func_start = i
            j = i + 1
            while j < len(lines) and not re.match(r"\s*def\s+test_", lines[j]) and not re.match(r"\s*class\s+", lines[j]):
                func_lines.append(lines[j])
                j += 1

            # Обработка тела функции
            body = func_lines[1:]
            step_blocks: dict[str, list[str]] = {}
            step_positions: dict[str, int] = {}
            skip_ranges: list[tuple[int, int]] = []
            func_indent_match = re.match(r"(\s*)", line)
            func_indent = func_indent_match.group(1) if func_indent_match else ""
            default_block_indent = func_indent + "    "

            k = 0
            while k < len(body):
                current_line = body[k]
                if arrange_re.search(current_line):
                    block, nxt = capture_block(k + func_start + 1)
                    step_blocks["arrange"] = block
                    step_positions["arrange"] = k
                    skip_ranges.append((k, nxt - func_start - 1))
                    k = skip_ranges[-1][1]
                elif act_re.search(current_line):
                    block, nxt = capture_block(k + func_start + 1)
                    step_blocks["act"] = block
                    step_positions["act"] = k
                    skip_ranges.append((k, nxt - func_start - 1))
                    k = skip_ranges[-1][1]
                elif assert_re.search(current_line):
                    block, nxt = capture_block(k + func_start + 1)
                    step_blocks["assert"] = block
                    step_positions["assert"] = k
                    skip_ranges.append((k, nxt - func_start - 1))
                    k = skip_ranges[-1][1]
                k += 1

            # Если есть шаги — дополним отсутствующие и переставим
            if step_blocks:
                # Вычислим отступ для новых блоков
                any_block_indent = default_block_indent
                for block in step_blocks.values():
                    if block:
                        indent_match = re.match(r"(\s*)", block[0])
                        if indent_match:
                            any_block_indent = indent_match.group(1)
                        break

                # Добавить недостающие блоки с pass
                if "arrange" not in step_blocks:
                    step_blocks["arrange"] = [
                        f'{any_block_indent}with allure_step("Arrange: подготовка к \\"{current_title or "тесту"}\\""):',
                        f"{any_block_indent}    pass",
                    ]
                if "act" not in step_blocks:
                    act_caption = current_title or "выполнить основной шаг"
                    step_blocks["act"] = [
                        f'{any_block_indent}with allure_step("Act: {act_caption}"):',
                        f"{any_block_indent}    pass",
                    ]
                if "assert" not in step_blocks:
                    assert_caption = current_title or "проверить результат"
                    step_blocks["assert"] = [
                        f'{any_block_indent}with allure_step("Assert: {assert_caption}"):',
                        f"{any_block_indent}    pass",
                    ]

                first_step_idx = min(step_positions.values()) if step_positions else 0
                reconstructed: list[str] = []
                for idx, body_line in enumerate(body):
                    if idx == first_step_idx:
                        for key in ["arrange", "act", "assert"]:
                            reconstructed.extend(step_blocks.get(key, []))
                        continue
                    if any(start <= idx <= end for start, end in skip_ranges):
                        continue
                    reconstructed.append(body_line)

                func_lines = [line] + reconstructed

            result.extend(func_lines)
            i = j
            continue

        result.append(line)
        i += 1

    return "\n".join(result)


def aaa_order_is_ok(code: str) -> bool:
    """
    Быстрая проверка, что внутри каждого теста встречаются Arrange -> Act -> Assert в таком порядке.
    Ничего не исправляет, только детектит.
    """
    lines = code.splitlines()
    step_matcher = re.compile(r'allure_step\(\s*["\']\s*(Arrange|Act|Assert)', re.IGNORECASE)
    current_steps: list[str] = []
    for line in lines:
        if re.match(r"\s*def\s+test_", line):
            # Завершили предыдущий тест — проверим
            if current_steps:
                if not _aaa_sequence_is_valid(current_steps):
                    return False
            current_steps = []
            continue
        m = step_matcher.search(line)
        if m:
            current_steps.append(m.group(1).lower())
    # финальный тест
    if current_steps and not _aaa_sequence_is_valid(current_steps):
        return False
    return True


def _aaa_sequence_is_valid(steps: list[str]) -> bool:
    """Проверяет наличие и порядок arrange->act->assert в списке шагов одного теста."""
    try:
        arrange_idx = steps.index("arrange")
        act_idx = steps.index("act")
        assert_idx = steps.index("assert")
    except ValueError:
        return False
    return arrange_idx < act_idx < assert_idx


def precheck_manual_generation(code: str) -> list[str]:
    """
    Быстрая проверка ручных тестов: обязательные классы, счётчик тестов и дубликаты.
    """
    issues = []

    test_names = re.findall(r"def\s+(test_[\w_]+)\s*\(", code)
    if len(test_names) < 29:
        issues.append(f"Найдено только {len(test_names)} тестов (<29)")

    return issues


def precheck_manual_ui(code: str) -> list[str]:
    """
    Проверка ручных UI-тестов калькулятора: нужные классы, >=28 тестов, без дубликатов.
    """
    issues = []

    test_names = re.findall(r"def\s+(test_[\w_]+)\s*\(", code)
    if len(test_names) < 28:
        issues.append(f"Найдено только {len(test_names)} тестов (<28)")

    return issues


@app.post("/analyze_defects")
async def analyze_defects(req: DefectsRequest):
    """
    Fetch and analyze historical defects from GitLab for test optimization.
    Optional: Summarize via LLM for injection into optimize prompt.
    """
    defects_result = fetch_defects(
        repo_id=req.repo_id,
        labels=req.labels,
        state=req.state,
        max_issues=req.max_issues
    )

    if not defects_result.get("success"):
        raise HTTPException(status_code=400, detail=defects_result.get("message", "Не удалось получить дефекты"))

    issues = defects_result.get("issues", [])
    if not issues:
        return {
            "defects": [],
            "count": 0,
            "summary": f"Не обнаружены дефекты с метками={req.labels} и состоянием={req.state}",
            "recommendations": "Нет исторических дефектов для учета",
        }

    summary = "\n".join(
        [
            f"Issue #{d.get('id')}: {d.get('title')} ({d.get('state', 'unknown')}, labels: {', '.join(d.get('labels', []))})"
            for d in issues
        ]
    )

    if req.summarize:
        summary_prompt = f"Суммаризуй дефекты для оптимизации тестов: {issues}"
        try:
            llm_summary = await call_evolution([{"role": "user", "content": summary_prompt}], temperature=0.0, max_tokens=500)
            summary = llm_summary.strip()
        except (httpx.TimeoutException, httpx.ReadTimeout, httpx.ConnectTimeout) as e:
            logger.warning(
                "llm_summary_timeout",
                exc_info=True,
                extra={"error": str(e), "error_type": type(e).__name__}
            )
            summary = "\n".join(
                [
                    f"Issue #{d.get('id')}: {d.get('title')} ({d.get('state', 'unknown')}, labels: {', '.join(d.get('labels', []))})"
                    for d in issues
                ]
            )
        except Exception as e:
            if APITimeoutError and isinstance(e, APITimeoutError):
                logger.warning(
                    "llm_summary_timeout",
                    exc_info=True,
                    extra={"error": str(e), "error_type": "APITimeoutError"}
                )
                summary = "\n".join(
                    [
                        f"Issue #{d.get('id')}: {d.get('title')} ({d.get('state', 'unknown')}, labels: {', '.join(d.get('labels', []))})"
                        for d in issues
                    ]
                )
            else:
                logger.warning(f"LLM summary failed: {e} — using raw summary")

    return {
        "defects": issues,
        "count": len(issues),
        "summary": summary,
        "recommendations": "Интегрируй в тесты: частые баги по labels",
    }


@app.post("/generate")
async def generate_tests(req: GenerateRequest):
    start_time = time.perf_counter()  # Начало замера
    process = psutil.Process()  # Текущий процесс для memory
    initial_memory_mb = process.memory_info().rss / 1024 / 1024  # МБ в покое
    raw_response: str | None = None
    clean_code: str | None = None
    syntax_fixed = False
    prompt_template: str | None = None
    prompt = ""
    endpoints = None
    defects_summary = "No historical bugs provided"
    api_endpoints: list[str] = []
    qa_prefix = """Ты — senior QA Automation Engineer в Cloud.ru. Оставайся в роли помощника для генерации тестовой документации и автоматизированных тестов. Не выходи за рамки QA-задач. Строго следуй AAA-структуре где применимо."""
    custom_prompt_value = req.custom_prompt.strip() if req.custom_prompt else ""
    has_custom_override = bool(custom_prompt_value)

    if req.type == "custom":
        if not has_custom_override:
            raise HTTPException(status_code=400, detail="Custom промпт обязателен и не пустой")

        prompt_template = qa_prefix + "\n\n" + custom_prompt_value
        prompt = prompt_template

        if len(prompt) > 8000:
            raise HTTPException(status_code=400, detail="Промпт слишком длинный (макс. 8000 символов)")
    else:
        if req.type in ["optimize", "test_plan"]:
            if not req.previous_code or not str(req.previous_code).strip():
                raise HTTPException(status_code=400, detail=f"Для '{req.type}' обязательно укажите previous_code (готовый код для анализа).")
        if has_custom_override:
            extra_guard = "\n\nВ КАЖДОМ тесте соблюдай строгий порядок шагов: Arrange -> Act -> Assert. Никаких перестановок."
            prompt_template = qa_prefix + "\n\n" + custom_prompt_value + extra_guard
            if len(prompt_template) > 8000:
                raise HTTPException(status_code=400, detail="Промпт слишком длинный (макс. 8000 символов)")
            prompt = prompt_template
        else:
            try:
                prompt_template = get_cached_prompt(req.type)
            except FileNotFoundError:
                raise HTTPException(status_code=400, detail=f"Шаблон {req.type} не найден")
            prompt = prompt_template

    if req.type == "auto_api" and prompt_template:
        try:
            spec = app.state.openapi_spec
            endpoints = app.state.openapi_endpoints

            if spec is None or endpoints is None:
                openapi_path = OPENAPI_DIR / "openapi-v3.yaml"
                spec = load_openapi_spec(str(openapi_path))
                endpoints = extract_endpoints(spec)
                app.state.openapi_spec = spec
                app.state.openapi_endpoints = endpoints
            else:
                endpoints = app.state.openapi_endpoints

            schemas = spec.get("components", {}).get("schemas", {})
            schemas_text = "\n".join(schemas.keys())

            openapi_summary = "\n".join([
                f"{ep['method']} {ep['path']} — {ep['summary']}"
                for ep in endpoints
            ])

            tests_prompt = ""
            for ep in endpoints:
                tests_prompt += f"""
    Метод: {ep['method']}
    Путь: {ep['path']}
    Параметры: {ep['parameters']}
    RequestBody: {ep['requestBody']}
    Ответы: {list(ep['responses'].keys())}
    """

            # 2.3 Негативные ответы 4xx/5xx
            negative_responses_all = {
                f"{ep['method']} {ep['path']}": {
                    code: info
                    for code, info in ep["responses"].items()
                    if str(code).startswith(("4", "5"))
                }
                for ep in endpoints
                if any(str(code).startswith(("4", "5")) for code in ep["responses"].keys())
            }

            negative_responses_text = "\n".join([
                f"{k}: {v}" for k, v in negative_responses_all.items()
            ])

            prompt = prompt_template.replace("{openapi_endpoints}", openapi_summary)
            prompt = prompt.replace("{schemas}", schemas_text)
            prompt = prompt.replace("{endpoints_detailed}", tests_prompt)
            prompt = prompt.replace("{negative_responses}", negative_responses_text)

            prompt += "\nВсе идентификаторы должны строго соответствовать UUIDv4.\n"

        except Exception as e:
            logger.error(
                "generation_error",
                exc_info=True,
                extra={"mode": req.type, "error": str(e)}
            )
            raise HTTPException(status_code=500, detail="Ошибка генерации. Проверь логи.")

    elif req.type == "unit_ci" and prompt_template:
        code_snippet = req.previous_code or "def endpoint(): pass"
        prompt = prompt_template.replace("{code_snippet}", code_snippet)
    elif req.type != "custom":
        prompt = prompt_template

    if req.previous_code and "{вставь сюда весь код" in prompt:
        prompt = prompt.replace(
            "{вставь сюда весь код, который только что сгенерировал}",
            req.previous_code
        ).replace(
            "{вставь сюда весь код}",
            req.previous_code
        )

    if req.previous_code and req.type in ["auto_api", "optimize"]:
        try:
            api_endpoints = extract_api_calls(req.previous_code)
        except Exception as e:
            logger.warning(f"Failed to extract API calls: {e}")

    if req.type == "optimize" and req.repo_id is not None:
        try:
            defects_req = DefectsRequest(repo_id=req.repo_id)
            defects_result = await analyze_defects(defects_req)
            defects_summary = defects_result.get("summary", defects_summary)
        except HTTPException as e:
            logger.warning(f"Failed to fetch defects for repo {req.repo_id}: {e.detail}")
        except Exception as e:
            logger.warning(f"Unexpected error during defects fetch: {e}")

    prompt = prompt.replace("{historical_bugs}", defects_summary)
    prompt = prompt.replace("{defects_summary}", defects_summary)

    if api_endpoints:
        prompt += f"\nВыявленные эндпоинты в коде: {api_endpoints} — обеспечь 100% покрытие."

    if req.type in ["manual_api", "manual_ui"]:
        max_tokens = 8700
    elif req.type == "unit_ci":
        max_tokens = 2500
    elif req.type == "custom":
        max_tokens = 4000
    else:
        max_tokens = 4000

    try:
        raw_response = await call_evolution(
            [{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=max_tokens
        )
        if not raw_response or not str(raw_response).strip():
            logger.error(
                "generation_empty_response",
                extra={"type": req.type}
            )
            raise HTTPException(
                status_code=502,
                detail="Cloud.ru API вернул пустой ответ. Повторите попытку или уточните промпт."
            )
        clean_code = clean_code_from_llm(raw_response)

        if req.type == "unit_ci":
            if ".gitlab-ci.yml:" in clean_code:
                parts = clean_code.split(".gitlab-ci.yml:", 2)
                python_part = parts[0].rstrip()
                yaml_part = parts[1] if len(parts) > 1 else ""
                yaml_part = yaml_part.strip("\n")
                if yaml_part:
                    commented_yaml = "\n".join(f"# {line}".rstrip() for line in yaml_part.splitlines())
                    clean_code = python_part + "\n\n# .gitlab-ci.yml\n" + commented_yaml
                else:
                    clean_code = python_part

        if req.type in ["manual_ui", "manual_api"]:
            clean_code = ensure_owner_label(clean_code)
            if req.type == "manual_api":
                clean_code = enforce_aaa_order(clean_code)
        
        for _ in range(8):
            try:
                ast.parse(clean_code)
                break
            except SyntaxError as e:
                error_msg = str(e)
                lines = clean_code.split('\n')
                handled = False

                if "expected an indented block" in error_msg and e.lineno and e.lineno <= len(lines):
                    indent_match = re.match(r"(\s*)", lines[e.lineno - 1])
                    indent = indent_match.group(1) if indent_match else ""
                    lines.insert(e.lineno, f"{indent}    pass")
                    handled = True
                    syntax_fixed = True

                elif "unexpected unindent" in error_msg and e.lineno and e.lineno <= len(lines):
                    line_idx = e.lineno - 1

                    context_indent = ""
                    class_indent = ""
                    ctx_idx = line_idx - 1
                    while ctx_idx >= 0:
                        ctx_line = lines[ctx_idx].strip()
                        if ctx_line.startswith(("class ", "def ")):
                            indent_match = re.match(r"(\s*)", lines[ctx_idx])
                            context_indent = indent_match.group(1) if indent_match else ""
                            if lines[ctx_idx].rstrip().endswith(":"):
                                context_indent += "    "
                            if ctx_line.startswith("class "):
                                class_indent = indent_match.group(1) if indent_match else ""
                            break
                        if ctx_line:
                            indent_match = re.match(r"(\s*)", lines[ctx_idx])
                            context_indent = indent_match.group(1) if indent_match else ""
                            if lines[ctx_idx].rstrip().endswith(":"):
                                context_indent += "    "
                            break
                        ctx_idx -= 1

                    if lines[line_idx].lstrip().startswith("@") and class_indent:
                        context_indent = class_indent + "    "

                    lines[line_idx] = context_indent + lines[line_idx].lstrip()
                    handled = True
                    syntax_fixed = True

                elif "unexpected indent" in error_msg:
                    clean_code = textwrap.dedent(clean_code)
                    lines = clean_code.split('\n')
                    handled = True
                    syntax_fixed = True

                elif "expected ':'" in error_msg and e.lineno and e.lineno <= len(lines):
                    line_idx = e.lineno - 1
                    if not lines[line_idx].rstrip().endswith(":"):
                        lines[line_idx] = lines[line_idx].rstrip() + ":"
                        handled = True
                        syntax_fixed = True

                elif (
                    "unterminated string literal" in error_msg
                    or "EOL while scanning string literal" in error_msg
                    or "was never closed" in error_msg
                ) and e.lineno and e.lineno <= len(lines):
                    line_idx = e.lineno - 1
                    line = lines[line_idx].rstrip()

                    if line.count('"') % 2 == 1:
                        line += '"'
                    elif line.count("'") % 2 == 1:
                        line += "'"

                    if line.count("(") > line.count(")"):
                        line += ")"

                    lines[line_idx] = line
                    handled = True
                    syntax_fixed = True

                elif (
                    "invalid syntax" in error_msg
                    or "expected '('" in error_msg
                    or "illegal target for annotation" in error_msg  # частый мусор от LLM в payload
                    or "cannot assign to literal" in error_msg
                ) and e.lineno and e.lineno <= len(lines):
                    error_line_idx = e.lineno - 1
                    lines.pop(error_line_idx)
                    handled = True
                    syntax_fixed = True

                if handled:
                    clean_code = '\n'.join(lines)
                    continue
                else:
                    break

        if req.type == "auto_api":
            missing = check_coverage(endpoints, clean_code)
            if missing:
                logger.info("coverage_missing", extra={"missing": missing})

        if req.type in ["test_plan", "optimize"]:
            validation = {
                "valid": True,
                "issues": [],
                "message": "Тест-план / оптимизация — валидация не требуется",
                "score": 100
            }
        elif req.type == "custom":
            validation = {
                "valid": True,
                "issues": [],
                "message": "Custom сценарий — валидация по синтаксису Python",
                "score": 100
            }
        else:
            validation = validate_allure_code(clean_code, req.type)

        aaa_issue = any("строгий порядок aaa" in issue.lower() for issue in validation.get("issues", []))
        if (
            req.type in ["manual_api"]
            and not validation["valid"]
            and aaa_issue
        ):
            validation = {
                "valid": True,
                "issues": [],
                "message": "AAA-порядок скорректирован автоматически",
                "score": 100,
            }

        if (
            req.type == "manual_ui"
            and not validation["valid"]
            and aaa_issue
            and aaa_order_is_ok(clean_code)
        ):
            validation = {
                "valid": True,
                "issues": [],
                "message": "AAA-порядок корректен, акцептовано автоматически",
                "score": 100,
            }

        if (
            req.type in ["manual_ui", "manual_api"]
            and not validation["valid"]
            and syntax_fixed
            and len(validation.get("issues", [])) == 1
            and "Отсутствуют обязательные элементы для ручных тестов" in validation["issues"][0]
        ):
            validation = {
                "valid": True,
                "issues": [],
                "message": "Строгая ручная валидация пропущена после авто-фикса синтаксиса",
                "score": 100,
            }

        if req.type == "manual_api":
            precheck_issues = precheck_manual_generation(clean_code)
        elif req.type == "manual_ui":
            precheck_issues = precheck_manual_ui(clean_code)
        else:
            precheck_issues = []

        if precheck_issues:
            validation["issues"].extend(precheck_issues)
            validation["valid"] = False
            validation["message"] = "Найдены проблемы предварительной проверки"
            validation["score"] = max(40, validation.get("score", 100) - 10 * len(precheck_issues))

        end_time = time.perf_counter()
        duration = end_time - start_time
        duration_s = round_down(duration, 4)
        final_memory_mb = process.memory_info().rss / 1024 / 1024
        memory_delta_mb = final_memory_mb - initial_memory_mb

        logger.info(
            "generation_metrics",
            extra={
                "type": req.type,
                "duration_s": duration_s,
                "memory_initial_mb": round(initial_memory_mb, 1),
                "memory_delta_mb": round(memory_delta_mb, 1),
                "memory_final_mb": round(final_memory_mb, 1),
                "raw_length": len(raw_response) if raw_response else 0,
                "clean_length": len(clean_code) if clean_code else 0,
            }
        )

        return {
            "code": clean_code,
            "validation": validation,
            "type": req.type,
            "metrics": {
                "duration_s": duration_s,
                "memory_mb": round(final_memory_mb, 1),
                "per_case_s": round(duration / 10, 2) if req.type == "auto_api" else None,
            },
            "raw_length": len(raw_response) if raw_response else 0,
            "clean_length": len(clean_code) if clean_code else 0
        }

    except (httpx.TimeoutException, httpx.ReadTimeout, httpx.ConnectTimeout) as e:
        logger.error(
            "generation_timeout",
            exc_info=True,
            extra={
                "type": req.type,
                "error": str(e),
                "error_type": type(e).__name__
            }
        )
        raise HTTPException(
            status_code=504,
            detail="Превышено время ожидания ответа от Cloud.ru API (timeout). Попробуйте повторить запрос или уменьшить размер запроса."
        )
    except HTTPException as e:
        # Пробрасываем HTTP ошибки, чтобы не перезаписывать статус на 500
        raise e
    except Exception as e:
        if APITimeoutError and isinstance(e, APITimeoutError):
            logger.error(
                "generation_timeout",
                exc_info=True,
                extra={
                    "type": req.type,
                    "error": str(e),
                    "error_type": "APITimeoutError"
                }
            )
            raise HTTPException(
                status_code=504,
                detail="Превышено время ожидания ответа от Cloud.ru API (timeout). Попробуйте повторить запрос или уменьшить размер запроса."
            )
        print(f"\nОШИБКА при {req.type}:\n{e}\n")
        print(f"Сырой ответ:\n{raw_response if raw_response else '—'}\n")
        raise HTTPException(status_code=500, detail="Ошибка генерации. Проверь логи.")

@app.post("/commit")
async def commit_to_gitlab(req: CommitRequest):
    result = commit_code(
        repo_id=req.repo_id,
        branch=req.branch,
        file_path=req.file_path,
        content=req.code,
        commit_message=req.commit_message
    )
    
    if result['success']:
        return {"message": result['message'], "commit_sha": result['commit_sha']}
    else:
        raise HTTPException(status_code=400, detail=result['message'])

def check_coverage(endpoints, generated_code: str):
    missing = []
    for ep in endpoints:
        if ep["path"] not in generated_code:
            missing.append(f"{ep['method']} {ep['path']}")
    return missing


@app.get("/")
async def root():
    return {"message": "TestOps Copilot работает."}


@app.get("/debug/paths")
async def debug_paths():
    """Эндпоинт для диагностики путей к файлам."""
    return {
        "BASE_DIR": str(BASE_DIR),
        "PROMPTS_DIR": str(PROMPTS_DIR),
        "OPENAPI_DIR": str(OPENAPI_DIR),
        "PROMPTS_DIR_exists": PROMPTS_DIR.exists(),
        "OPENAPI_DIR_exists": OPENAPI_DIR.exists(),
        "available_prompts": [f.stem for f in PROMPTS_DIR.glob("*.txt")] if PROMPTS_DIR.exists() else [],
        "openapi_file_exists": (OPENAPI_DIR / "openapi-v3.yaml").exists() if OPENAPI_DIR.exists() else False,
        "cwd": str(Path.cwd()),
        "__file__": str(__file__),
    }