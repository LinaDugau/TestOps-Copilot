# TestOps Copilot - Интеллектуальный помощник для автоматической генерации тестов

## 📖 Описание проекта

TestOps Copilot - это инструмент для автоматической генерации тестов различных типов с использованием LLM модели Cloud.ru Evolution. Приложение состоит из backend (FastAPI) и frontend (React) частей.

### Обратная связь по проекту

Делимся обратной связью по вашему решению.

Что особенно понравилось:
Решение выглядит сильным и цельным - по сути это MVP уровня v1.1 с продуманной архитектурой и широким функциональным покрытием. Реализованы все ключевые режимы из ТЗ: генерация ручных и автоматических тест-кейсов, формирование тест-планов, валидация и оптимизация.
Архитектура backend выполнена на высоком уровне: FastAPI с четким разделением слоев, структурированное логирование, большое количество unit-тестов, multi-stage Docker. Код читаемый, хорошо документированный и легко поддерживаемый.
LLM-часть реализована особенно качественно: асинхронная работа с Cloud.ru, Jinja-промпты под разные режимы, подмешивание контекста из OpenAPI и истории дефектов GitLab, автофиксы кода, умная валидация, ретраи и таймауты.
Отдельно хочется отметить оптимизацию тестов с учетом исторических дефектов, генерацию тест-планов, CI на GitLab, использование Commit API, покрытие OpenAPI и наличие метрик времени и памяти. Frontend дополняет систему, README очень подробный, вход в проект для нового разработчика максимально упрощен.

Что важно улучшить:
Зоны роста носят скорее эволюционный характер. В текущей реализации отсутствует кэширование ответов LLM, что может влиять на производительность и стоимость при масштабировании - это выглядит как логичный следующий шаг для такого решения.
Также пользовательский интерфейс выглядит функциональным, но менее насыщенным по UX по сравнению с уровнем backend-части. При дальнейшем развитии можно усилить визуализацию, навигацию по тестам, планам и результатам оптимизации.

Проект полностью закрывает требования ТЗ и демонстрирует глубокое понимание TestOps, архитектуры и практической работы с LLM. При этом на фоне других сильных решений он воспринимается скорее как очень зрелый и аккуратно реализованный инженерный продукт, чем как решение с дополнительным рывком в продуктовой или пользовательской части. Именно в сравнении с другими работами это стало сдерживающим фактором :((
При небольших доработках в части кэширования и UI решение выглядит готовым к дальнейшему развитию и практическому использованию.

Спасибо за участие и проделанную работу!

### Возможности

- 🤖 **Автоматическая генерация тестов** - 6 различных режимов генерации
- 📝 **Ручные тест-кейсы** - Для UI и API (18+ тест-кейсов каждый)
- ⚙️ **Автоматические тесты** - e2e UI тесты и API тесты с использованием OpenAPI
- 📋 **Генератор тест-планов** - Структурированные тест-планы на основе кода
- 🔧 **Оптимизация тестов** - Анализ и оптимизация существующих тестов
- 🧪 **Unit-тесты для CI/CD** - Быстрые pytest тесты для FastAPI + .gitlab-ci.yml
- 🐞 **Анализ дефектов** - Загрузка исторических GitLab issues (bug/defect) для улучшения оптимизации
- ✅ **Валидация Allure** - Автоматическая проверка соответствия стандартам

### ⚡ Производительность

- **Ручные тест-кейсы (30 кейсов):** ~23 секунды, память ~97 МБ
- **Автоматические тесты:** ~13 секунд, память ~97 МБ
- **Скорость генерации:** ~1,12 секунд на один промпт
- **Покрытие тестами:** 92%

## 🚀 Способы запуска

### 1. Docker Compose (Рекомендуется) 🐳

Самый простой способ запуска - через Docker Compose. Один контейнер содержит и backend, и frontend.

#### Шаг 1: Настройка переменных окружения

Создайте файл `backend/.env`:

```bash
cd backend
echo CLOUD_RU_API_KEY=your_api_key_here > .env
echo CLOUD_RU_MODEL=Qwen/Qwen3-Next-80B-A3B-Instruct >> .env
```

#### Шаг 2: Запуск контейнера

```bash
# Из корневой директории проекта
# Сборка и запуск
docker-compose up -d --build

# Или если образ уже собран
docker-compose up -d
```

#### Шаг 3: Проверка работы

Откройте в браузере: `http://localhost`

**Важно:** 
- `.env` файл должен находиться в директории `backend/`
- Docker Compose автоматически читает `backend/.env` и передает переменные в контейнер
- GitLab токены (опционально) можно добавить в `.env` для интеграции с GitLab

#### Управление контейнером

```bash
# Остановить контейнер
docker-compose stop

# Запустить снова
docker-compose start

# Посмотреть логи
docker-compose logs -f

# Посмотреть логи только backend
docker-compose logs -f app

# Пересобрать после изменений
docker-compose up -d --build

# Остановить и удалить контейнер
docker-compose down

# Остановить и удалить контейнер с volumes
docker-compose down -v
```

### 2. Docker (без docker-compose)

Альтернативный способ запуска через Docker напрямую:

```bash
# Сборка образа
docker build -t testops-copilot .

# Запуск с переменными окружения
docker run -d -p 80:80 \
  -e CLOUD_RU_API_KEY=your_api_key_here \
  -e CLOUD_RU_MODEL=Qwen/Qwen3-Next-80B-A3B-Instruct \
  --name testops-copilot \
  testops-copilot

# Или с .env файлом
docker run -d -p 80:80 \
  --env-file backend/.env \
  --name testops-copilot \
  testops-copilot
```

### 3. Локальная разработка

Если нужно запустить backend и frontend отдельно для разработки:

#### Backend (локально)

```bash
cd backend

# Создание виртуального окружения
python -m venv venv

# Активация виртуального окружения
venv\Scripts\activate

# Установка зависимостей
pip install -r requirements.txt

# Настройка .env файла
echo CLOUD_RU_API_KEY=your_api_key_here > .env
echo CLOUD_RU_MODEL=Qwen/Qwen3-Next-80B-A3B-Instruct >> .env

# Запуск сервера
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Backend будет доступен на `http://localhost:8000`

**Проверка работы:**
```bash
curl http://localhost:8000/
# Должен вернуться: {"message": "TestOps Copilot работает на 100%..."}
```

**Документация API:** `http://localhost:8000/docs` (Swagger UI)

#### Frontend (локально)

```bash
cd frontend

# Установка зависимостей
npm install

# Запуск development сервера
npm start
```

Frontend будет доступен на `http://localhost:3000` и автоматически откроется в браузере.

**Важно:** Убедитесь, что backend запущен на `http://localhost:8000`, иначе frontend не сможет отправлять запросы.

### 4. Production запуск

Для production окружения рекомендуется использовать Docker Compose с дополнительными настройками:

```yaml
# docker-compose.prod.yml (пример)
version: '3.8'
services:
  app:
    build: .
    ports:
      - "80:80"
    env_file:
      - backend/.env
    restart: always
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/"]
      interval: 30s
      timeout: 10s
      retries: 3
```

Запуск:
```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

### Примеры запуска

#### Пример 1: Быстрый старт с минимальной конфигурацией

```bash
# 1. Создать .env файл
cd backend
echo CLOUD_RU_API_KEY=your_key > .env
cd ..

# 2. Запустить
docker-compose up -d --build

# 3. Открыть браузер
# http://localhost
```

#### Пример 2: Локальная разработка с hot-reload

```bash
# Terminal 1: Backend
cd backend
python -m venv venv
source venv\Scripts\activate 
pip install -r requirements.txt
echo CLOUD_RU_API_KEY=your_key > .env
uvicorn main:app --reload --port 8000

# Terminal 2: Frontend
cd frontend
npm install
npm start
```

#### Пример 3: Запуск с GitLab интеграцией

```bash
# Создать .env с GitLab токенами
cd backend
cat > .env << EOF
CLOUD_RU_API_KEY=your_cloud_ru_key
CLOUD_RU_MODEL=Qwen/Qwen3-Next-80B-A3B-Instruct
GITLAB_URL=https://gitlab.com
GITLAB_TOKEN=glpat-your_token
EOF
cd ..

# Запустить
docker-compose up -d --build
```

## 📡 API Документация

### Эндпоинт `/generate`

Основной эндпоинт для генерации тестов.

**Метод:** `POST`  
**URL:** `http://localhost/generate` (Docker) или `http://localhost:8000/generate` (локально)

#### Request Body

```json
{
  "type": "string",           // Тип генерации (обязательно)
  "previous_code": "string",  // Предыдущий код (опционально)
  "repo_id": "string"         // ID/path GitLab для учета багов в optimize (опционально)
}
```

#### Доступные типы генерации

| Тип | Описание |
|-----|----------|
| `manual_ui` | Ручные UI тесты для калькулятора (18+ кейсов) |
| `manual_api` | Ручные API тесты для Evolution Compute (18+ кейсов) |
| `auto_ui` | Автоматические e2e UI тесты (Playwright + pytest) |
| `auto_api` | Автоматические API тесты (pytest + requests + OpenAPI) |
| `test_plan` | Генератор тест-плана (требует previous_code) |
| `optimize` | Оптимизация тестов (требует previous_code) |
| `unit_ci` | Unit-тесты для FastAPI + .gitlab-ci.yml для CI/CD |

- **repo_id** (опционально для `optimize`): если передать ID или путь GitLab проекта, backend подтянет issues с label `bug/defect` и учтёт их при оптимизации.

#### Response

```json
{
  "code": "string",           // Сгенерированный код
  "validation": {
    "valid": true,            // Статус валидации
    "issues": [],             // Найденные проблемы
    "message": "string",      // Сообщение
    "score": 100              // Оценка (0-100)
  },
  "type": "string",           // Тип запроса
  "raw_length": 1234,         // Длина сырого ответа
  "clean_length": 1200        // Длина очищенного кода
}
```

#### Пример запроса

```bash
# Для Docker
curl -X POST "http://localhost/generate" \
  -H "Content-Type: application/json" \
  -d '{"type": "auto_api"}'

# Для локального запуска
curl -X POST "http://localhost:8000/generate" \
  -H "Content-Type: application/json" \
  -d '{"type": "auto_api"}'
```

#### Особенности режима `auto_api`

- Автоматически загружает OpenAPI спецификацию из `backend/openapi/openapi-v3.yaml`
- Извлекает все эндпоинты, схемы и параметры
- Генерирует тесты с учетом реальной спецификации
- Проверяет покрытие всех эндпоинтов
- Все идентификаторы соответствуют формату UUIDv4

### Эндпоинт `/analyze_defects`

**Метод:** `POST`  
**URL:** `http://localhost/analyze_defects` (Docker) или `http://localhost:8000/analyze_defects` (локально)

Request Body:
```json
{
  "repo_id": "group/project-or-id",
  "labels": ["bug"],
  "state": "opened",
  "max_issues": 10,
  "summarize": true
}
```

Response (сокращённо):
```json
{
  "count": 3,
  "summary": "LLM summary of bugs ...",
  "defects": [{ "id": 123, "title": "...", "labels": ["bug"] }],
  "recommendations": "Интегрируй в тесты: частые баги по labels"
}
```

Использование: передайте `repo_id` в `/generate` для режима `optimize`, чтобы баги из GitLab были подставлены в промпт через плейсхолдер `{defects_summary}` / `{historical_bugs}`.

## 📸 Скриншоты

Скриншоты работы приложения находятся в папке [`photo/`](photo/):

1. **Главный экран** - Интерфейс выбора типа генерации
2. **Генерация тестов** - Процесс генерации и результаты
3. **Валидация** - Проверка соответствия стандартам Allure
4. **Сгенерированный код** - Примеры с подсветкой синтаксиса
5. **Оптимизация** - Режим анализа и оптимизации тестов
6. **Тест-план** - Пример сгенерированного тест-плана

## 🏗️ Архитектура

### Общая структура проекта

```
testops-copilot/
├── backend/                      # FastAPI backend
│   ├── main.py                   # Главный файл приложения, API endpoints
│   ├── config.py                 # Конфигурация и настройки (Pydantic Settings)
│   ├── cloud_ru.py               # Интеграция с Cloud.ru Evolution API
│   ├── validator.py              # Валидатор Allure кода
│   ├── openapi_parser.py         # Парсер OpenAPI спецификации
│   ├── gitlab_client.py          # Интеграция с GitLab API
│   ├── logging_config.py         # Настройка логирования
│   ├── prompts/                  # Шаблоны промптов для LLM (Jinja2)
│   │   ├── auto_api.jinja       # Промпт для автоматических API тестов
│   │   ├── auto_ui.jinja        # Промпт для автоматических UI тестов
│   │   ├── manual_api.jinja     # Промпт для ручных API тестов
│   │   ├── manual_ui.jinja      # Промпт для ручных UI тестов
│   │   ├── test_plan.jinja      # Промпт для генерации тест-плана
│   │   ├── optimize.jinja       # Промпт для оптимизации тестов
│   │   └── unit_ci.jinja        # Промпт для unit-тестов CI/CD
│   ├── openapi/                  # OpenAPI спецификации
│   │   └── openapi-v3.yaml      # Спецификация Evolution Compute API
│   ├── .env                      # Переменные окружения (создать вручную)
│   ├── requirements.txt          # Python зависимости
│   ├── pytest.ini                # Конфигурация pytest
│   └── tests/                    # Тесты backend (покрытие 92%)
│       ├── test_main.py
│       ├── test_cloud_ru.py
│       ├── test_validator.py
│       └── ...
├── frontend/                      # React frontend
│   ├── src/
│   │   ├── App.tsx               # Главный компонент приложения
│   │   ├── App.css               # Стили приложения
│   │   ├── index.tsx             # Точка входа React
│   │   └── ...
│   ├── public/                   # Статические файлы
│   ├── nginx.conf                # Конфигурация nginx для Docker
│   ├── package.json              # Node.js зависимости
│   └── tsconfig.json             # Конфигурация TypeScript
├── docker/                        # Docker конфигурация
│   ├── supervisord.conf          # Управление процессами (backend + nginx)
│   └── start.sh                  # Скрипт запуска контейнера
├── Dockerfile                     # Multi-stage образ (frontend builder + backend)
├── docker-compose.yml             # Конфигурация Docker Compose
└── README.md                      # Этот файл
```

### Архитектурные компоненты

#### Backend (FastAPI)
- **API Layer** (`main.py`): REST API endpoints для генерации тестов
- **LLM Integration** (`cloud_ru.py`): взаимодействие с Cloud.ru Evolution API
- **Validation Layer** (`validator.py`): проверка соответствия стандартам Allure
- **OpenAPI Parser** (`openapi_parser.py`): извлечение эндпоинтов из OpenAPI спецификации
- **GitLab Integration** (`gitlab_client.py`): коммит тестов и анализ дефектов
- **Prompt Templates** (`prompts/`): шаблоны Jinja2 для различных типов генерации

#### Frontend (React)
- **UI Components**: Material-UI компоненты для интерфейса
- **API Client**: Axios для HTTP запросов к backend
- **Code Display**: react-syntax-highlighter для отображения кода

#### Infrastructure
- **Nginx**: reverse proxy для статических файлов и API запросов
- **Supervisor**: управление процессами backend и nginx в контейнере
- **Docker**: контейнеризация всего приложения

### Поток данных

1. **Пользователь** → Frontend (React) → выбор типа генерации
2. **Frontend** → Backend API (`/generate`) → POST запрос с типом
3. **Backend** → загрузка промпта из `prompts/` (Jinja2 шаблон)
4. **Backend** → Cloud.ru Evolution API → генерация кода через LLM
5. **Backend** → валидация кода (`validator.py`) → очистка и проверка
6. **Backend** → Frontend → возврат сгенерированного кода и результатов валидации
7. **Frontend** → отображение кода с подсветкой синтаксиса

## 🧪 Тестирование

### Backend тесты

```bash
cd backend

# Запуск всех тестов
pytest

# Запуск с покрытием
pytest --cov=. --cov-report=html

# Запуск конкретного теста
pytest tests/test_main.py

# Запуск с подробным выводом
pytest -v
```

**Текущее покрытие: 92%** (отчёт доступен в `backend/htmlcov/index.html` после прогона `pytest --cov`).

### Frontend тесты

```bash
cd frontend

# Запуск тестов
npm test

# Запуск тестов в watch режиме
npm test -- --watch

# Запуск тестов с покрытием
npm test -- --coverage
```

## 🔧 Конфигурация и переменные окружения

### Backend конфигурация

Создайте файл `backend/.env` в корне директории `backend/`:

```env
# Обязательные переменные
CLOUD_RU_API_KEY=your_api_key_here
CLOUD_RU_MODEL=Qwen/Qwen3-Next-80B-A3B-Instruct

# Опциональные переменные (для GitLab интеграции)
GITLAB_URL=https://gitlab.com
GITLAB_TOKEN=your_gitlab_token_here
```

#### Описание переменных окружения

| Переменная | Обязательная | Описание | Пример значения |
|-----------|--------------|----------|-----------------|
| `CLOUD_RU_API_KEY` | ✅ Да | Bearer token для Cloud.ru Evolution API | `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...` |
| `CLOUD_RU_MODEL` | ❌ Нет | Модель LLM для генерации (по умолчанию: `Qwen/Qwen3-Next-80B-A3B-Instruct`) | `Qwen/Qwen3-Next-80B-A3B-Instruct` |
| `GITLAB_URL` | ❌ Нет | URL GitLab instance для коммита тестов и анализа дефектов | `https://gitlab.com` или `https://gitlab.example.com` |
| `GITLAB_TOKEN` | ❌ Нет | GitLab Personal Access Token с правами `api` и `write_repository` | `glpat-xxxxxxxxxxxxxxxxxxxx` |

#### Где получить API ключ Cloud.ru

1. Зайдите в [Cloud.ru Console](https://console.cloud.ru/)
2. Перейдите в раздел "API Keys" или "Токены доступа"
3. Создайте новый Bearer token
4. Скопируйте ключ в файл `backend/.env`

#### Где получить GitLab токен (опционально)

1. Зайдите в GitLab
2. Перейдите в **Settings** → **Access Tokens** (или **User Settings** → **Access Tokens**)
3. Создайте токен с правами:
   - `api` - для чтения issues и анализа дефектов
   - `write_repository` - для коммита тестов в репозиторий
4. Скопируйте токен в файл `backend/.env`
5. Укажите `GITLAB_URL` (например, `https://gitlab.com` или URL вашего GitLab instance)

### Frontend конфигурация

В Docker контейнере frontend автоматически использует относительные пути для API запросов (проксирование через nginx). При локальной разработке frontend использует `http://localhost:8000` для API запросов.

Для изменения адреса backend в development режиме отредактируйте `frontend/src/App.tsx`:

```typescript
const API_URL = 'http://localhost:8000'; // или ваш адрес backend
```

### Примеры конфигурации

#### Минимальная конфигурация (только генерация тестов)

```env
# backend/.env
CLOUD_RU_API_KEY=your_api_key_here
```

#### Полная конфигурация (с GitLab интеграцией)

```env
# backend/.env
CLOUD_RU_API_KEY=your_api_key_here
CLOUD_RU_MODEL=Qwen/Qwen3-Next-80B-A3B-Instruct
GITLAB_URL=https://gitlab.com
GITLAB_TOKEN=glpat-xxxxxxxxxxxxxxxxxxxx
```

#### Конфигурация для корпоративного GitLab

```env
# backend/.env
CLOUD_RU_API_KEY=your_api_key_here
CLOUD_RU_MODEL=Qwen/Qwen3-Next-80B-A3B-Instruct
GITLAB_URL=https://gitlab.company.com
GITLAB_TOKEN=glpat-xxxxxxxxxxxxxxxxxxxx
```

### Проверка конфигурации

После создания `.env` файла проверьте, что переменные загружены корректно:

```bash
# В Docker
docker-compose logs app | grep "CLOUD_RU_API_KEY"

# Локально (после запуска backend)
curl http://localhost:8000/
# Должен вернуться: {"message": "TestOps Copilot работает на 100%..."}
```

## 📚 Документация

- [API Docs](http://localhost/docs) - Интерактивная Swagger документация (Docker) или [http://localhost:8000/docs](http://localhost:8000/docs) (локально)

## 🛠️ Технологический стек

### Backend
- **FastAPI** 0.123.10 - современный веб-фреймворк для создания API
- **Python** 3.12 - язык программирования
- **Uvicorn** 0.38.0 - ASGI сервер для запуска FastAPI
- **Pydantic** 2.12.5 - валидация данных и настройки
- **Cloud.ru Evolution API** - интеграция с LLM моделью (Qwen/Qwen3-Next-80B-A3B-Instruct)
- **OpenAPI Spec Validator** 0.7.1 - валидация и парсинг OpenAPI спецификаций
- **python-gitlab** 4.9.0 - интеграция с GitLab API для коммита тестов и анализа дефектов
- **Jinja2** 3.1.6 - шаблонизация промптов для LLM
- **PyYAML** 6.0.3 - парсинг YAML файлов (OpenAPI спецификации)
- **pytest** 8.3.4 - фреймворк для тестирования
- **pytest-cov** 6.0.0 - измерение покрытия кода тестами
- **httpx** 0.28.1 - асинхронный HTTP клиент для API запросов
- **psutil** 5.9.8 - мониторинг использования ресурсов

### Frontend
- **React** 19.2.1 - библиотека для построения пользовательских интерфейсов
- **TypeScript** 4.9.5 - типизированный JavaScript
- **Material-UI (MUI)** 7.3.6 - компонентная библиотека для React
- **Axios** 1.13.2 - HTTP клиент для запросов к API
- **react-syntax-highlighter** 16.1.0 - подсветка синтаксиса кода
- **react-scripts** 5.0.1 - инструменты для сборки React приложения

### DevOps & Инфраструктура
- **Docker** - контейнеризация приложения
- **Docker Compose** - оркестрация контейнеров
- **Nginx** - веб-сервер и reverse proxy для статических файлов и API
- **Supervisor** - управление процессами в контейнере (backend + nginx)
- **Node.js** 18 - среда выполнения для сборки frontend

## 👥 Авторы

Команда ХХ
