# knowledge-service

Microservicio RAG (Retrieval-Augmented Generation) desacoplado. Gestiona una base
de conocimiento con modelos de IA locales y expone la funcionalidad vía REST.

> **Estado:** scaffolding. La infraestructura está preparada; la lógica de IA
> (embeddings, Qdrant, Ollama, parsing de PDF) aún no está implementada.

## Arquitectura

Clean Architecture + DDD ligero. Las dependencias apuntan siempre al dominio.

```
app/
  api/             # Capa HTTP: routers, schemas, DI wiring, error handlers
  application/     # Casos de uso, DTOs (orquestación)
  domain/          # Entidades, value objects, eventos, puertos (ABCs). Puro Python
  infrastructure/  # Adaptadores concretos (placeholders por ahora)
  shared/          # Logging, tipos comunes, constantes
  config/          # Settings centralizados (pydantic-settings)
  workers/         # Procesamiento en background (reservado)
```

Reglas de capa validadas en CI con `import-linter`.

## Requisitos

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)
- Docker + Docker Compose

## Puesta en marcha

```bash
cp .env.example .env
make install       # instala dependencias
make run           # API local con reload -> http://localhost:8000
```

Con Docker (FastAPI + PostgreSQL + Qdrant):

```bash
docker compose up --build
```

> Ollama corre **fuera** del compose (acceso a GPU y ciclo de vida propio).
> Configúralo vía `LLM_BASE_URL`.

## Endpoints (scaffolding)

Todos responden `501 Not Implemented` por ahora.

| Método | Ruta                     |
|--------|--------------------------|
| GET    | `/health`                |
| POST   | `/api/v1/documents/upload`  |
| POST   | `/api/v1/documents/process` |
| POST   | `/api/v1/chat`              |
| POST   | `/api/v1/search`            |

Docs OpenAPI: `http://localhost:8000/docs`

## Comandos

```bash
make check     # lint + typecheck + contracts + tests
make lint
make format
make typecheck
make test
make migrate   # alembic upgrade head
```
