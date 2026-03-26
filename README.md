# Resume Analyzer API

AI сервис для анализа резюме на основе LangGraph. Принимает PDF или TXT файл, запускает четыре специализированных агента параллельно и возвращает детальный отчёт с оценками и рекомендациями.

## Архитектура

```
┌─────────────────────────────────────────────────────────────┐
│                        FastAPI                               │
│   POST /analyze    GET /history    GET /{id}                 │
└──────────────────────────┬──────────────────────────────────┘
                           │
                    ResumeService
                           │
          ┌────────────────┴────────────────┐
          │                                 │
    LangGraph Graph                   ResumeRepository
          │                                 │
          │  ┌─────────────────────┐        │
          │  │   Параллельные      │        │
          ├──│   агенты            │     PostgreSQL
          │  │                     │
          │  │  analyze_skills     │
          │  │  analyze_experience │
          │  │  analyze_structure  │
          │  │  analyze_language   │
          │  └────────┬────────────┘
          │           │
          │    compile_report
          │
          └───────────┘
```

## Стек

- **Python 3.11**
- **FastAPI** — REST API
- **LangGraph** — оркестрация агентов
- **LangChain + Groq** — LLM (llama-3.3-70b-versatile)
- **PostgreSQL 16** — хранение истории анализов
- **SQLAlchemy** — асинхронный ORM
- **Docker + docker-compose** — контейнеризация
- **Ruff + mypy** — линтеры
- **pytest + testcontainers** — тесты

## Быстрый старт

### Требования

- Docker
- Docker Compose
- Бесплатный API ключ Groq: [console.groq.com](https://console.groq.com)

### Установка

```bash
git clone https://github.com/boshka22/langchain_start
cd resume-analyzer
```

Создай `.env` файл:

```env
GROQ_API_KEY=твой-ключ

POSTGRES_DB=resume_analyzer
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres

DATABASE_URL=postgresql+asyncpg://postgres:postgres@postgres:5432/resume_analyzer
```

Запусти:

```bash
docker-compose up --build
```

API доступен на [http://localhost:8000/docs](http://localhost:8000/docs)

## Эндпоинты

| Метод | Путь | Описание |
|-------|------|----------|
| `POST` | `/api/v1/resume/analyze` | Анализ резюме (PDF или TXT) |
| `GET` | `/api/v1/resume/history` | История анализов с пагинацией |
| `GET` | `/api/v1/resume/{id}` | Получение анализа по ID |
| `GET` | `/health` | Проверка работоспособности |

## Пример ответа

```json
{
  "status": "success",
  "overall_score": 8,
  "summary": "Резюме демонстрирует широкий стек и конкретные достижения с цифрами.",
  "criteria": {
    "skills": {
      "score": 9,
      "feedback": "Актуальный стек, хорошее покрытие технологий.",
      "suggestions": [
        "Добавить уровни владения технологиями",
        "Указать конкретные версии"
      ]
    },
    "experience": {
      "score": 9,
      "feedback": "Конкретные достижения с цифрами, хорошая прогрессия.",
      "suggestions": [
        "Добавить ссылку на GitHub",
        "Описать командную работу"
      ]
    },
    "structure": {
      "score": 7,
      "feedback": "Структура понятная, но есть лишние блоки.",
      "suggestions": [
        "Убрать дублирующиеся контакты",
        "Добавить раздел Summary"
      ]
    },
    "language": {
      "score": 8,
      "feedback": "Профессиональный тон, сильные глаголы действия.",
      "suggestions": [
        "Убрать клише",
        "Сократить длинные предложения"
      ]
    }
  },
  "top_strengths": [
    "Конкретные метрики и достижения",
    "Современный и релевантный стек",
    "Прогрессия карьеры"
  ],
  "top_improvements": [
    "Добавить раздел Summary",
    "Указать уровни владения навыками",
    "Убрать лишнюю информацию"
  ],
  "file_name": "resume.pdf"
}
```

## Структура проекта

```
resume_analyzer/
├── app/
│   ├── api/
│   │   └── v1/
│   │       └── resume.py        # роутеры
│   ├── core/
│   │   ├── config.py            # настройки
│   │   └── database.py          # подключение к БД
│   ├── database/
│   │   └── models.py            # SQLAlchemy модели
│   ├── graph/
│   │   ├── state.py             # состояние графа
│   │   ├── nodes.py             # узлы агентов
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
│   └── main.py                  # FastAPI приложение
├── tests/
│   ├── unit/
│   │   └── test_parsers.py
│   └── integration/
│       ├── test_api.py
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

## Roadmap

- [x] Анализ резюме через LangGraph с параллельными агентами
- [x] Поддержка PDF и TXT
- [x] Сохранение истории в PostgreSQL
- [x] Чистая архитектура (api / services / graph / repositories)
- [x] Docker + docker-compose
- [x] Линтеры (ruff, mypy) и pre-commit хуки
- [x] Тесты с testcontainers
- [ ] Async LangGraph агенты
- [ ] Celery + Redis для фоновой обработки
- [ ] Кэширование результатов через Redis
- [ ] Аутентификация (JWT)
- [ ] Веб-интерфейс
- [ ] Сравнение резюме с вакансией
- [ ] Экспорт отчёта в PDF
- [ ] LangSmith для мониторинга агентов
- [ ] Kubernetes deployment
