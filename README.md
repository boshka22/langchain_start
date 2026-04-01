# Resume Analyzer API

AI сервис для анализа резюме на основе LangGraph. Принимает PDF или TXT файл, запускает четыре специализированных агента параллельно через Celery и возвращает детальный отчёт с оценками и рекомендациями.

## Архитектура

```
┌─────────────────────────────────────────────────────────────┐
│                        FastAPI                               │
│  POST /analyze   GET /analyze/{task_id}/status               │
│  GET /history    GET /{id}                                   │
└──────────────────────────┬──────────────────────────────────┘
                           │
                    ┌──────▼──────┐
                    │    Redis     │
                    │  cache hit?  │
                    └──────┬──────┘
               HIT ◄───────┴───────► MISS
           (мгновенно)              (202 + task_id)
                                         │
                                  Celery Worker
                                         │
                     ┌───────────────────┴────────────────┐
                     │                                     │
               LangGraph Graph                    ResumeRepository
                     │                                     │
               ┌─────────────┐                         PostgreSQL
               │  Параллельные│
               │   агенты     │
               │              │
               │ analyze_skills
               │ analyze_experience
               │ analyze_structure
               │ analyze_language
               └──────┬───────┘
                      │
               compile_report
                      │
               сохранить в БД + кэш Redis (TTL 24ч)
                      │
         (опционально) webhook → callback_url
```

## Стек

- **Python 3.11**
- **FastAPI** — REST API
- **LangGraph** — оркестрация агентов
- **LangChain** — интеграция с LLM провайдерами
- **Celery + Redis** — фоновая обработка и очередь задач
- **Redis Cache** — кэширование результатов (Cache-Aside, TTL 24ч)
- **PostgreSQL 16** — хранение истории анализов
- **SQLAlchemy** — асинхронный ORM
- **Docker + docker-compose** — контейнеризация
- **Ruff + mypy** — линтеры
- **pytest + testcontainers** — тесты

## Поддерживаемые LLM провайдеры

Провайдер выбирается через переменную `LLM_PROVIDER` в `.env`. Менять код не нужно.

| Провайдер | Модель по умолчанию | Где взять ключ |
|-----------|---------------------|----------------|
| `groq` | `llama-3.3-70b-versatile` | [console.groq.com](https://console.groq.com) — бесплатно |
| `gemini` | `gemini-2.0-flash` | [aistudio.google.com](https://aistudio.google.com) — бесплатно |
| `ollama` | `llama3.2` | Локально, без ключей — [ollama.com](https://ollama.com) |

## Быстрый старт

### Требования

- Docker + Docker Compose

### Установка

```bash
git clone https://github.com/boshka22/langchain_start
cd resume-analyzer
```

Создай `.env` файл и выбери провайдер:

```env
# ── LLM провайдер ──────────────────────────────
# Выбери один: groq | gemini | ollama
LLM_PROVIDER=groq
MODEL_NAME=llama-3.3-70b-versatile

# Groq (бесплатно, https://console.groq.com)
GROQ_API_KEY=твой-ключ

# Gemini (бесплатно, https://aistudio.google.com)
# LLM_PROVIDER=gemini
# MODEL_NAME=gemini-2.0-flash
# GOOGLE_API_KEY=твой-ключ

# Ollama (локально, без ключей)
# LLM_PROVIDER=ollama
# MODEL_NAME=llama3.2
# OLLAMA_BASE_URL=http://host.docker.internal:11434

# ── Инфра ──────────────────────────────────────
POSTGRES_DB=resume_analyzer
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
DATABASE_URL=postgresql+asyncpg://postgres:postgres@postgres:5432/resume_analyzer
REDIS_URL=redis://redis:6379/0
```

Запусти:

```bash
docker-compose up --build
```

API доступен на [http://localhost:8000/docs](http://localhost:8000/docs)

### Ollama (локальная модель, без ключей)

```bash
# Установи Ollama с ollama.com, затем:
ollama pull llama3.2

# В .env выставь:
# LLM_PROVIDER=ollama
# MODEL_NAME=llama3.2
```

## Как работает асинхронный анализ

### Без кэша (первый запрос)

```
1. POST /analyze + файл
   → X-Cache: MISS
   → 202 Accepted {"task_id": "uuid", "status": "pending", "cached": false}

2. GET /analyze/{task_id}/status  →  {"status": "started", "result": null}
3. GET /analyze/{task_id}/status  →  {"status": "success", "result": {...}}
```

### С кэшем (повторный запрос того же резюме)

```
1. POST /analyze + файл
   → X-Cache: HIT
   → 202 Accepted {"task_id": "cached", "status": "success", "cached": true, "result": {...}}
```

Повторный запрос возвращает результат мгновенно — Celery не задействуется.
Кэш живёт 24 часа, ключ — MD5 хэш текста резюме.

Опционально — передай `callback_url` в форме запроса. Когда анализ завершится, воркер сам сделает POST на этот URL с результатом.

## Эндпоинты

| Метод | Путь | Описание |
|-------|------|----------|
| `POST` | `/api/v1/resume/analyze` | Запустить анализ резюме (PDF или TXT) |
| `GET` | `/api/v1/resume/analyze/{task_id}/status` | Статус задачи и результат |
| `GET` | `/api/v1/resume/history` | История анализов с пагинацией |
| `GET` | `/api/v1/resume/{id}` | Получение анализа по ID из БД |
| `GET` | `/health` | Проверка работоспособности |

## Примеры ответов

### Новый анализ (кэш MISS)

```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "cached": false,
  "result": null
}
```

### Результат из кэша (кэш HIT)

```json
{
  "task_id": "cached",
  "status": "success",
  "cached": true,
  "result": {
    "status": "success",
    "overall_score": 8,
    "summary": "Резюме демонстрирует широкий стек и конкретные достижения с цифрами.",
    "criteria": {
      "skills": {
        "score": 9,
        "feedback": "Актуальный стек, хорошее покрытие технологий.",
        "suggestions": ["Добавить уровни владения технологиями", "Указать конкретные версии"]
      },
      "experience": {
        "score": 9,
        "feedback": "Конкретные достижения с цифрами, хорошая прогрессия.",
        "suggestions": ["Добавить ссылку на GitHub", "Описать командную работу"]
      },
      "structure": {
        "score": 7,
        "feedback": "Структура понятная, но есть лишние блоки.",
        "suggestions": ["Убрать дублирующиеся контакты", "Добавить раздел Summary"]
      },
      "language": {
        "score": 8,
        "feedback": "Профессиональный тон, сильные глаголы действия.",
        "suggestions": ["Убрать клише", "Сократить длинные предложения"]
      }
    },
    "top_strengths": ["Конкретные метрики и достижения", "Современный стек", "Прогрессия карьеры"],
    "top_improvements": ["Добавить раздел Summary", "Указать уровни владения навыками"],
    "file_name": "resume.pdf"
  }
}
```

## Структура проекта

```
resume_analyzer/
├── app/
│   ├── api/
│   │   └── v1/
│   │       └── resume.py        # роутеры
│   ├── cache/
│   │   └── resume.py            # Cache-Aside кэширование в Redis
│   ├── core/
│   │   ├── config.py            # настройки
│   │   └── database.py          # подключение к БД
│   ├── database/
│   │   └── models.py            # SQLAlchemy модели
│   ├── graph/
│   │   ├── state.py             # состояние графа
│   │   ├── nodes.py             # узлы агентов + фабрика LLM
│   │   └── builder.py           # сборка графа
│   ├── parsers/
│   │   └── file.py              # парсинг PDF/TXT
│   ├── repositories/
│   │   └── resume.py            # слой БД
│   ├── schemas/
│   │   └── v1/
│   │       └── resume.py        # Pydantic схемы
│   ├── services/
│   │   └── resume.py            # бизнес-логика
│   ├── tasks/
│   │   └── analyze.py           # Celery таск
│   ├── celery_app.py            # инициализация Celery
│   └── main.py                  # FastAPI приложение
├── tests/
│   ├── unit/
│   │   └── test_parsers.py
│   └── integration/
│       ├── test_api.py
│       ├── test_cache.py
│       └── test_repository.py
├── docker-compose.yml
├── Dockerfile
├── pyproject.toml
└── requirements.txt
```

## Разработка

### Запуск тестов

```bash
# Все тесты (testcontainers автоматически поднимет PostgreSQL)
pytest tests/ -v

# Только юнит тесты
pytest tests/unit/ -v

# Только интеграционные
pytest tests/integration/ -v
```

### Линтеры

```bash
ruff check app/
ruff format app/
mypy app/
```

### Pre-commit хуки

```bash
pre-commit install
pre-commit run --all-files
```

### Проверка кэша в Redis

```bash
# Зайти в Redis CLI
docker exec -it resume_analyzer_redis redis-cli

# Посмотреть все ключи кэша
KEYS resume:analysis:*

# Проверить TTL ключа
TTL resume:analysis:<хэш>
```

## Roadmap

- [x] Анализ резюме через LangGraph с параллельными агентами
- [x] Поддержка PDF и TXT
- [x] Сохранение истории в PostgreSQL
- [x] Чистая архитектура (api / services / graph / repositories)
- [x] Celery + Redis — фоновая обработка, поллинг статуса
- [x] Webhook уведомления (callback_url)
- [x] Поддержка нескольких LLM провайдеров (Groq, Gemini, Ollama)
- [x] Кэширование результатов через Redis (Cache-Aside, TTL 24ч)
- [x] Docker + docker-compose
- [x] Линтеры (ruff, mypy) и pre-commit хуки
- [x] Тесты с testcontainers
- [ ] Аутентификация (JWT)
- [ ] Сравнение резюме с вакансией
- [ ] Экспорт отчёта в PDF
- [ ] LangSmith для мониторинга агентов
- [ ] Kubernetes deployment
