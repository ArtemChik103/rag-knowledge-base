---
title: Rag Knowledge Base
emoji: 🔍
colorFrom: indigo
colorTo: blue
sdk: docker
app_port: 7860
pinned: false
license: mit
---

# RAG Knowledge Base System

[![Live Demo](https://img.shields.io/badge/Live_Demo-Render-46E3B7?style=flat-square&logo=render&logoColor=white)](https://rag-knowledge-base-jhms.onrender.com)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18-61DAFB?style=flat-square&logo=react&logoColor=black)](https://reactjs.org)
[![ChromaDB](https://img.shields.io/badge/ChromaDB-Vector_Store-orange?style=flat-square)](https://www.trychroma.com)

Мини-сервис для загрузки текстовых документов (регламентов, инструкций), их векторизации в ChromaDB и выполнения семантического поиска с генерацией точных ответов и цитированием источников.

**🌐 Онлайн-демо (Cloud):** [https://rag-knowledge-base-jhms.onrender.com](https://rag-knowledge-base-jhms.onrender.com)

---

## 1. Возможности сервиса

- **Поддержка форматов:** PDF (с сохранением номеров страниц), TXT, Markdown.
- **Векторная база данных:** ChromaDB с постоянным локальным хранилищем и HNSW-индексом по косинусному расстоянию.
- **Быстрые легковесные эмбеддинги:** `cointegrated/rubert-tiny2` (312 измерений) + квантованный ONNX Runtime INT8 (28 MB, sub-millisecond inference).
- **Точные ответы и цитирование:** Синтез ответов с указанием названий документов, номеров страниц, индексов чанков и оценок сходства.
- **Генератор тестового регламента:** Автоматическое создание многостраничного регламента компании ООО «ТехноИнновации» в формате PDF.
- **Веб-интерфейс:** React + Vite + Tailwind CSS SPA со строгой визуальной иерархией, телеметрией задержки и инспектором чанков.


---

## 2. Структура проекта

```
zadanie/
├── backend/
│   ├── config.py              # Конфигурация и переменные окружения
│   ├── document_parser.py     # Модуль парсинга PDF/TXT/MD с разбивкой по страницам
│   ├── text_splitter.py       # Рекурсивное разбиение текста на чанки с перекрытием
│   ├── vector_store.py        # Обертка ChromaDB, ONNX Runtime и эмбеддинги
│   ├── rag_engine.py          # Логика поиска, ранжирования и синтеза ответа
│   ├── generate_sample_pdf.py # Скрипт генерации корпоративного регламента в PDF
│   └── main.py                # FastAPI сервер и раздача статики
├── frontend/                  # React + Vite + Tailwind пользовательский интерфейс
│   ├── src/
│   ├── package.json
│   └── vite.config.js
├── tests/                     # Набор автоматических тестов (pytest)
│   ├── test_parser.py
│   ├── test_splitter.py
│   ├── test_vector_store.py
│   └── test_api.py
├── Dockerfile                 # Multi-stage сборка для Docker и Hugging Face Spaces
├── sample_company_policy.pdf  # Пример регламента для проверки
├── SOLUTION_LOGIC.md          # Подробное описание логики решения
├── ALGORITHM.md               # Формальное математическое описание алгоритмов
├── requirements.txt           # Зависимости Python
├── LICENSE                    # MIT License
└── README.md                  # Руководство пользователя
```

---

## 3. Установка и запуск

### 3.1. Требования к окружению
- Python 3.10+
- Node.js 18+ (для сборки фронтенда)

### 3.2. Установка зависимостей Python

```cmd
python -m pip install -r requirements.txt
```

### 3.3. Сборка фронтенда

```cmd
cd frontend
npm install
npm run build
cd ..
```

### 3.4. Запуск сервера

```cmd
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

После запуска сервис доступен по адресу:
- Веб-интерфейс: `http://127.0.0.1:8000/`
- Интерактивная документация Swagger: `http://127.0.0.1:8000/docs`

---

## 4. REST API Спецификация

| Метод | Путь | Описание |
|---|---|---|
| `POST` | `/api/documents/upload` | Загрузить и проиндексировать документ (PDF, TXT, MD) |
| `GET` | `/api/documents` | Получить список загруженных документов и их статистику |
| `GET` | `/api/documents/{doc_id}/chunks` | Получить список чанков конкретного документа |
| `DELETE` | `/api/documents/{doc_id}` | Удалить документ и его векторы из базы |
| `POST` | `/api/query` | Выполнить семантический поиск и получить ответ на вопрос |
| `POST` | `/api/sample-document` | Сгенерировать и проиндексировать тестовый регламент PDF |
| `GET` | `/api/stats` | Получить системную статистику базы знаний |
| `POST` | `/api/reset` | Полная очистка векторной базы |
| `GET` | `/api/health` | Проверка состояния сервиса |

### Пример запроса на поиск:

```bash
curl -X POST "http://127.0.0.1:8000/api/query" \
  -H "Content-Type: application/json" \
  -d '{"query": "Каков размер компенсации расходов на спорт?", "top_k": 4}'
```

---

## 5. Запуск автоматических тестов

Запустите тестовый набор через `pytest`:

```cmd
python -m pytest -v
```

---

## 6. Лицензия

Проект распространяется под лицензией MIT. Подробности в файле [LICENSE](LICENSE).
