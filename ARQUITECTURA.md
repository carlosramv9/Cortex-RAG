# Walkthrough de arquitectura — knowledge-service

> Documento de onboarding técnico. Recorrido completo de la arquitectura del
> proyecto para un desarrollador con experiencia en .NET/React, principiante en
> Python. Explica el **por qué**, no solo el **qué**.

**Nota de contexto:** el `README.md` dice "scaffolding / todo responde 501".
Está **desactualizado**. El commit `51c7477` implementó de verdad la ingesta de
documentos, el versionado, la metadata tipada y el pipeline asíncrono. Lo que
sigue siendo scaffolding es la parte de IA (parsing real, embeddings, Qdrant,
LLM). Se señala módulo por módulo.

---

## 0. La idea rectora

Todo el proyecto obedece **una regla**:

> **Las dependencias apuntan siempre hacia el dominio. El dominio no apunta a nada.**

Esto es Clean Architecture / Arquitectura Hexagonal (puertos y adaptadores). En
.NET: es la mentalidad de una solución con proyectos `Domain`, `Application`,
`Infrastructure`, `Api` donde `Domain` no referencia a nadie y todos referencian
a `Domain`. Diferencia: en Python no hay `.csproj` que impida una referencia
mala, así que la regla se **impone con un linter** (`import-linter`, sección 13).
Ese linter es el compilador de arquitectura que .NET da gratis.

El "por qué" de fondo: la lógica de negocio (qué es un documento, cuándo un job
puede pasar de QUEUED a RUNNING, qué es un duplicado) debe poder existir,
testearse y razonarse **sin** FastAPI, PostgreSQL, Qdrant ni Ollama. Esas cuatro
cosas son detalles reemplazables. El negocio no.

---

## 1. Estructura de carpetas

```
app/
  api/             # Capa HTTP. Traduce HTTP <-> casos de uso.
  application/     # Casos de uso (orquestación) + DTOs.
  domain/          # El corazón. Entidades, value objects, eventos, PUERTOS (ABCs). Python puro.
  infrastructure/  # Adaptadores concretos: SQLAlchemy, Qdrant, Ollama, filesystem.
  workers/         # Procesamiento en background (fuera del request HTTP).
  config/          # Settings centralizados (pydantic-settings).
  shared/          # Utilidades transversales sin negocio: logging, hashing, constantes, parsing.
alembic/           # Migraciones de esquema de BD.
docker/            # Dockerfile + entrypoint.
scripts/           # Entrypoints ejecutables (seed, run_worker).
tests/             # unit/ + integration/.
```

Por qué existe cada una y qué pasaría si desapareciera:

- **`domain/`** — Razón de ser del sistema. Define *qué es* el negocio con tipos
  puros. Si desapareciera, no habría producto. Única capa que no depende de
  ninguna otra.
- **`application/`** — Orquesta el dominio para cumplir un caso de uso concreto.
  Si desapareciera, la lógica se filtraría a los routers (endpoints gordos) o al
  dominio (entidades acopladas a storage). Existe para que haya **un** lugar por
  operación de negocio, reutilizable desde HTTP y desde un worker.
- **`api/`** — Frontera HTTP. Convierte JSON/multipart en DTOs, invoca el caso de
  uso, mapea excepciones de dominio a códigos HTTP. Si desapareciera, perderías
  REST pero el negocio seguiría intacto (gRPC, CLI). Intencionalmente **fina y
  desechable**.
- **`infrastructure/`** — Implementaciones concretas de los puertos. El "cómo".
  Si desapareciera, dominio y aplicación **compilarían igual** (dependen de
  abstracciones), pero no habría dónde persistir en runtime. Capa más volátil.
- **`workers/`** — Trabajo pesado fuera del ciclo request/response. Si
  desapareciera, la API aceptaría uploads pero los `ProcessingJob` quedarían en
  QUEUED para siempre. Proceso **separado** (`scripts/run_worker.py`).
- **`config/`** — Única fuente de verdad de configuración. Si desapareciera,
  aparecerían `os.getenv()` dispersos (anti-patrón que el proyecto prohíbe).
- **`shared/`** — Utilidades sin negocio ni framework (hashing, logging,
  constantes, parsing). Puede ser importado por cualquier capa **incluido el
  dominio**. Es el "kernel común".

La separación permite que el `import-linter` verifique en CI que nadie rompió las
flechas de dependencia.

---

## 2. Flujo completo de un request

Caso canónico `POST /api/v1/documents`:

```
   Cliente (multipart: file + knowledge_space_id, headers X-Tenant-Id/X-User-Id)
       │
       ▼
   ┌─────────────────────────────────────────────────────────────┐
   │ FastAPI (app/main.py)                                        │
   │  · CORS middleware                                           │
   │  · timing middleware  → header X-Process-Time-Ms + log      │
   └─────────────────────────────────────────────────────────────┘
       │
       ▼
   ROUTER  app/api/v1/routers/documents.py :: upload_document()
       │   params: UploadDocumentUseCaseDep, TenantIdDep, UploadedByDep, UploadFile
       │
       ▼
   DEPENDENCY INJECTION  app/api/dependencies.py  (Composition Root)
       │   FastAPI resuelve el árbol Depends de abajo hacia arriba:
       │     get_database(app.state) → get_session() ─┐
       │     get_settings() → get_upload_settings()   │
       │     get_document_repository(session)         ├─► construye
       │     get_storage_provider(settings)           │   UploadDocumentUseCase
       │     get_event_publisher()                    │
       │     get_create_processing_job_use_case(...) ─┘
       │
       ▼
   USE CASE  app/application/documents/use_cases/upload_document.py :: execute()
       │   valida → checksum → dedup → guarda bytes → crea entidades →
       │   repo.add() → publica evento → crea ProcessingJob (QUEUED)
       │
       ▼
   REPOSITORY (puerto)  app/domain/documents/repositories.py :: DocumentRepository (ABC)
       │        ▲ implementado por
   REPOSITORY (adaptador)  infrastructure/.../document_repository.py
       │   mapea Entidad → Modelo SQLAlchemy, session.add(), session.flush()
       │
       ▼
   BASE DE DATOS  PostgreSQL (vía asyncpg)
       │   al salir del context manager de la sesión → COMMIT (o ROLLBACK si excepción)
       │
       ▼
   RESPONSE  el use case devuelve DocumentView (Pydantic) → JSON 201
       │   si ConflictError → app/api/errors.py lo mapea a HTTP 409
       ▼
   Cliente
```

Dos detalles cruciales:

1. **El `commit` no lo hace el use case ni el repositorio.** Lo hace el context
   manager de la sesión (`Database.session()` en `session.py`): `yield` → sin
   excepción `commit`; con excepción `rollback`. Los repos solo hacen `flush`.
   Patrón **Unit of Work** implícito con alcance de request. En .NET: el
   `AsyncSession` = `DbContext`; el `async with` = `SaveChangesAsync` automático
   al cierre del scope.
2. **La transacción abarca todo el use case.** Documento + versión + job en la
   misma sesión → o todo o nada. Atomicidad de negocio.

---

## 3. La capa Domain

Ubicación `app/domain/`. Python puro. Sin `import sqlalchemy` ni `import fastapi`
(el linter lo garantiza, sección 13).

### Entidades (`documents/entities.py`, `jobs.py`)

`@dataclass(slots=True)`. En .NET: clases de entidad / aggregate roots POCO.

- **`KnowledgeDocument`** — *Aggregate root*. Identidad lógica y permanente. No
  contiene filename, size ni checksum. Solo identidad estable: `id`, `tenant_id`,
  `title`, `source_type`, `status`, `current_version_id`, `metadata`. Regla de
  negocio como propiedad: `is_deleted`.
- **`KnowledgeDocumentVersion`** — Archivo físico inmutable. Aquí viven
  `filename`, `size`, `checksum_sha256`, `storage_path`. Invariante: las versiones
  nunca se modifican ni se borran. `current_version_id` apunta a la activa.
- **`KnowledgePage`, `KnowledgeChunk`** — Preparadas. `KnowledgeChunk` es el
  centro del sistema RAG (fragmento recuperable); existe desde ya. Mantiene la
  cadena de trazabilidad: `Chunk → Page → Document → bytes originales`.
- **`ProcessingJob`** (`jobs.py`) — **Máquina de estados** con transiciones como
  métodos: `start()`, `advance()`, `complete()`, `fail()`, `cancel()`, `retry()`.
  Cada transición valida el estado origen y lanza `ValidationError` si es ilegal.
  Es *tell, don't ask*: le pides al job que se mueva y él protege sus invariantes.

### Value Objects (`documents/value_objects.py`, `metadata.py`)

- **`BoundingBox`** — `@dataclass(frozen=True, slots=True)`. Inmutable, comparado
  por valor. Reservado para resaltar texto sobre la página.
- **`KnowledgeMetadata`** — Es un **`BaseModel` de Pydantic**, no dataclass.
  ¿Por qué? Necesita validación rica (idioma ISO 639-1, tags sin duplicados,
  `extra="forbid"`) y serialización JSON sin pérdida. Pydantic es librería de
  validación, no framework de app ni persistencia → el linter la permite en el
  dominio. Excepción pragmática a "el dominio es dataclasses puros".

### Eventos (`documents/events.py`, `shared/events.py`)

`DomainEvent` base con `event_id` y `occurred_at` autogenerados. Todos
`frozen=True`. Los concretos son `kw_only=True` porque heredan campos con default.

### Interfaces / Puertos (`repositories.py`, `providers.py`)

`ABC` con `@abstractmethod`. Mecanismo central de inversión de dependencias.
Equivalen 1:1 a `interface IDocumentRepository` en C#. (Detalle en sección 15.)

### ¿Por qué el dominio no depende de SQLAlchemy?

SQLAlchemy es detalle de persistencia. Si `KnowledgeDocument` fuera modelo
SQLAlchemy: no lo instanciarías en un test sin BD/registry; un cambio de columna
arrastraría negocio; atarías el modelo mental a la forma de una tabla. Como
dataclass puro, se crea en memoria en microsegundos sin infraestructura.

### ¿Por qué no conoce FastAPI?

FastAPI es detalle de transporte. "Un documento duplicado no se admite dos veces"
es verdad por HTTP, CLI o worker. Si el dominio lanzara `HTTPException(409)`,
amarrarías una regla de negocio a un protocolo. Lanza `ConflictError`
(framework-agnóstico) y `api/errors.py` la traduce a 409.

---

## 4. La capa Application

Ubicación `app/application/`.

### ¿Qué es un Use Case?

Clase que representa una operación de negocio completa. Anatomía constante:

```python
class UploadDocumentUseCase:
    def __init__(self, documents, storage, events, upload_settings, create_job):
        # recibe PUERTOS (abstracciones), nunca implementaciones concretas
    async def execute(self, data: UploadDocumentInput) -> DocumentView:
        # orquesta: valida → checksum → dedup → store → persist → evento → job
```

Colaboradores por constructor (tipados como puertos del dominio), un único
`execute()`.

### ¿Por qué no meter la lógica en el endpoint?

El endpoint `upload_document` hace tres cosas: (1) lee bytes del `UploadFile`,
(2) arma `UploadDocumentInput`, (3) llama `use_case.execute()`. Cero negocio.
Meter la lógica en el endpoint sería: no reutilizable (no invocable desde worker
sin arrastrar FastAPI), no testeable en aislamiento (necesitas TestClient HTTP
para probar dedup), violaría SRP (router con dos razones para cambiar).

### Paralelo .NET (Command Handler / MediatR)

| Este proyecto (Python) | .NET / MediatR |
|---|---|
| `UploadDocumentInput` (DTO Pydantic) | `UploadDocumentCommand : IRequest<DocumentView>` |
| `UploadDocumentUseCase.execute()` | `UploadDocumentHandler.Handle()` |
| Colaboradores por constructor (puertos) | Dependencias inyectadas en el handler |
| `DocumentView` (DTO salida) | El `TResponse` del `IRequest<>` |

Diferencia: no hay mediador/bus. El router referencia el use case directamente
vía `Depends`. MediatR "sin el Send()", más explícito, sin reflexión.

Composición notable: `UploadDocumentUseCase` recibe **otro use case** como
colaborador (`CreateProcessingJobUseCase`). Tras subir el documento, delega la
creación del job. Composición de casos de uso, no duplicación.

Los **DTOs** (`application/*/dtos.py`) son la frontera de datos.
`DocumentView.from_document()` **aplana** el aggregate: fusiona identidad +
versión activa en un objeto plano para el cliente REST.

---

## 5. La capa Infrastructure

Ubicación `app/infrastructure/`. Todos los **adaptadores concretos**:

- `persistence/sqlalchemy/` — modelos ORM, repositorios, sesión/engine, base.
- `storage/local_storage.py` — `LocalStorageProvider` (filesystem).
- `events/logging_publisher.py` — `LoggingEventPublisher`.
- `embeddings/`, `llm/`, `parsers/`, `vector_store/`, `chunking/` — adaptadores de
  IA (mayoría scaffolding).

### ¿Por qué los repositorios concretos viven aquí?

Un repositorio concreto es puro detalle de infra: sabe de `AsyncSession`,
`select()`, tablas, mapeo modelo↔entidad. `SqlAlchemyDocumentRepository`
implementa el puerto `DocumentRepository`. Infra apunta al dominio (implementa su
ABC), el dominio no sabe que infra existe. Migrar a Mongo = escribir
`MongoDocumentRepository` y cambiar **una línea** en el Composition Root.

### ¿Por qué `StorageProvider` es implementación y no interfaz?

Cuidado, dos cosas con nombres parecidos:

- **`app/domain/storage/providers.py :: StorageProvider`** → **SÍ es interfaz**
  (ABC abstracta `save/load/delete`). Vive en el dominio. Es el *puerto*.
- **`app/infrastructure/storage/local_storage.py :: LocalStorageProvider`** → la
  **implementación** concreta (el *adaptador*).

Comparten raíz del nombre, distintas capas. Convención: puerto `XxxProvider`/
`XxxRepository` en `domain/`; adaptadores anteponen la tecnología (`Local`,
`SqlAlchemy`, `Ollama`, `Qdrant`, `PyMuPDF`).

La interfaz existe aunque hoy solo haya local storage porque permite: (a) testear
con `InMemoryStorage` sin tocar disco; (b) añadir S3 mañana
(`StorageProviderKind.S3` ya existe) sin tocar use case ni dominio.

Calidad en `LocalStorageProvider`: I/O bloqueante delegada con
`asyncio.to_thread(...)` para no congelar el event loop; `_resolve()` previene
path traversal.

---

## 6. Dependency Injection

### Composition Root: `app/api/dependencies.py`

> *"The ONLY place where the api layer is allowed to import from infrastructure."*

Único punto donde se cruza la línea api→infra. Aquí los puertos del dominio se
atan a los adaptadores concretos. Es tu `Program.cs` / `ConfigureServices`, pero
**sin contenedor de IoC**: FastAPI usa DI basado en funciones (`Depends`).

### Cómo FastAPI obtiene un UseCase

Patrón repetido: función provider + alias `Annotated`.

```python
def get_document_repository(session: SessionDep) -> DocumentRepository:
    return SqlAlchemyDocumentRepository(session)          # puerto ← adaptador

DocumentRepositoryDep = Annotated[DocumentRepository, Depends(get_document_repository)]
```

```
POST /documents llega
   ▼
FastAPI ve param  use_case: UploadDocumentUseCaseDep
   ▼
resuelve get_upload_document_use_case(...) — 5 dependencias:
   ├─ DocumentRepositoryDep
   │     └─ get_document_repository(session)
   │           └─ SessionDep → get_session(database)
   │                 └─ DatabaseDep → get_database(request)
   │                       └─ request.app.state.database   ← creado en lifespan (startup)
   │        ⇒ new SqlAlchemyDocumentRepository(session)
   ├─ StorageProviderDep ⇒ new LocalStorageProvider(path)
   ├─ EventPublisherDep ⇒ new LoggingEventPublisher()
   ├─ UploadSettingsDep → settings.upload
   └─ CreateProcessingJobUseCaseDep ⇒ new CreateProcessingJobUseCase(...)
   ▼
⇒ new UploadDocumentUseCase(...)  → inyectado en el router → await use_case.execute(input)
   ▼
al terminar el request: get_session sale de su `async with` → COMMIT
```

Qué recordar:

- **Scope = request.** Cada petición: sesión nueva. `get_session` es generador;
  el código tras `yield` corre al cerrar el request (commit/rollback). Repos y use
  cases se construyen frescos por request. = `AddScoped` en .NET.
- **Singletons de proceso.** `Database` (engine + pool) se crea una vez en
  `lifespan` (`main.py`), en `app.state.database`. `get_settings()` cacheado con
  `@lru_cache`. = `AddSingleton`.
- **Todo tipado contra puertos.** Las `get_*` devuelven el tipo abstracto
  (`-> DocumentRepository`). Momento exacto de la inversión de dependencias.

Error común: construir un adaptador dentro del router o use case en vez de dejarlo
al Composition Root. Rompe testabilidad y contrato de capas.

---

## 7. PostgreSQL: de modelo SQLAlchemy a entidad de dominio

### Dos mundos separados

- **Modelo (infra):** `KnowledgeDocumentModel` en `models.py`. Hereda de `Base`.
  Fila de tabla: columnas, índices, FKs, `TimestampMixin`.
- **Entidad (dominio):** `KnowledgeDocument` en `entities.py`. Dataclass puro.

No comparten clase. No es active record. Dos representaciones + mapeo explícito.

### ¿Dónde ocurre el mapping?

En el repositorio, funciones puras a nivel de módulo (`document_repository.py`):

```python
def _doc_to_entity(model, active_version) -> KnowledgeDocument: ...
def _doc_to_model(entity) -> KnowledgeDocumentModel: ...
def _version_to_entity(model) -> KnowledgeDocumentVersion: ...
def _version_to_model(entity) -> KnowledgeDocumentVersionModel: ...
```

Traducción no trivial: columna `meta` (JSON) → value object tipado con
`KnowledgeMetadata.model_validate(model.meta)` al leer, y de vuelta con
`entity.metadata.model_dump(mode="json")` al escribir. El dominio ve
`KnowledgeMetadata`; la BD ve JSON.

Al leer, el repo **rehidrata la versión activa** (`_load_version`) y la pone en
`entity.active_version` (campo runtime-only, no columna).

### ¿Por qué separarlos?

1. El dominio queda libre de SQLAlchemy.
2. La forma de la tabla puede divergir de la forma del negocio.
3. **Portabilidad de tests:** tipos genéricos (`Uuid`, `JSON`) a propósito para
   que el mismo esquema corra en PostgreSQL (prod) y SQLite (tests). Los tests de
   integración montan SQLite en memoria con `Base.metadata.create_all`.

En .NET: distinción entre entidad de dominio y EF entity/configuration, con mapper
en medio.

---

## 8. Alembic (migraciones)

Equivalente a **EF Migrations**. Config en `alembic/env.py`:

```python
config.set_main_option("sqlalchemy.url", get_settings().db.async_dsn)  # reusa settings
from app.infrastructure.persistence.sqlalchemy import models  # noqa  ← import por side-effect
target_metadata = Base.metadata
```

1. No duplica la URL de BD: la toma de `Settings`.
2. Importa `models` **por su efecto secundario**: al importarse, cada
   `class XxxModel(Base)` se registra en `Base.metadata`. Sin ese import, Alembic
   no vería tablas al autogenerar. Gotcha típico de Python, aquí resuelto.

Corre async. `entrypoint.sh` ejecuta `alembic upgrade head` **antes** de arrancar
la API.

### Cadena de migraciones actual

```
098482a100da  (knowledge ingestion foundation)   ← base, down_revision = None
      ↓
b7f2c9a4d1e8  (document versioning)
      ↓
c3d9e1f42a76  (typed metadata and source_type)
      ↓
d4e8f1a29b30  (processing job pipeline)           ← head
```

Punto didáctico: la migración base (`098482a100da`) crea `knowledge_documents`
con columnas físicas inline y `processing_jobs` con `attempts`/`payload`. Pero
`models.py` **hoy** tiene `knowledge_documents` sin esas columnas + una tabla
`knowledge_document_versions` aparte, y jobs con `retry_count`/`progress`/
`worker_name`.

**Las migraciones son un registro histórico incremental, no una foto del estado
actual.** El esquema final = aplicar las 4 en orden. Nunca edites una migración
aplicada; añades una nueva.

### Qué hacer al agregar una entidad

1. Define el modelo ORM en `models.py` (`class FooModel(Base)`), con
   `TimestampMixin` si aplica.
2. `models.py` ya se importa en `env.py`.
3. Genera: `alembic revision --autogenerate -m "add foo"`.
4. **Revisa** el archivo generado (Alembic no detecta renombres, algunos cambios
   de tipo, índices sutiles). El `# please adjust!` es en serio.
5. Aplica: `alembic upgrade head` (o `make migrate`).
6. Archivos que participan: `models.py`, `env.py`, `alembic.ini`,
   `script.py.mako`, el nuevo archivo en `versions/`.

---

## 9. Settings

Ubicación `app/config/settings.py`. Sobre **pydantic-settings** (= `IOptions<T>`
+ binding de config de .NET, con validación de tipos incorporada).

### Filosofía

Un único objeto `Settings`, compuesto de sub-settings por dominio funcional, cada
uno con su prefijo de entorno:

```
Settings
 ├─ app:        AppSettings        (env_prefix="APP_")
 ├─ db:         DatabaseSettings   (env_prefix="DB_")
 ├─ vector:     VectorSettings     (env_prefix="VECTOR_")
 ├─ llm:        LLMSettings        (env_prefix="LLM_")
 ├─ embedding:  EmbeddingSettings  (env_prefix="EMBEDDING_")
 ├─ storage:    StorageSettings    (env_prefix="STORAGE_")
 ├─ upload:     UploadSettings     (env_prefix="UPLOAD_")
 └─ processing: ProcessingSettings (env_prefix="PROCESSING_")
```

### Cómo llegan las variables del `.env` al código

1. `Settings.model_config` declara `env_file=".env"`. Al instanciar `Settings()`,
   lee el `.env` + variables de entorno.
2. Cada sub-clase declara su `env_prefix`. `DB_HOST=...` puebla
   `DatabaseSettings.host`; `APP_LOG_JSON=true` puebla `AppSettings.log_json`.
3. **Coerción de tipos automática:** `DB_PORT=5432` (string) → `int`. Si pusieras
   `abc`, error de validación al arranque (*fail fast*).
4. **Campos computados:** `DatabaseSettings.async_dsn` es `@computed_field` que
   construye el DSN `postgresql+asyncpg://…`. Nadie arma esa cadena a mano.
5. **Singleton cacheado:** `get_settings()` con `@lru_cache(maxsize=1)`. Una
   instancia; `main.py`, `alembic/env.py` y `run_worker.py` comparten config.

### Parsers reutilizables (`shared/parsing.py`)

Problema: pydantic-settings, para campos complejos (`list`, `dict`), JSON-decodea
el valor del env *antes* de tus validadores. `CORS_ORIGINS=*,https://foo.com`
(formato humano) explotaría por no ser JSON.

Solución en tres piezas:
1. `Annotated[list[str], NoDecode]` → `NoDecode` desactiva el JSON-decode
   automático; el string crudo llega al validador.
2. `@field_validator(mode="before")` que llama `parse_str_list(value)`.
3. `parse_str_list` acepta tres formas: lista ya hecha (passthrough de defaults),
   string JSON (`'["a","b"]'` → `json.loads`), o CSV (`'a, b'` → split + trim).

Resultado: `UPLOAD_ALLOWED_EXTENSIONS=pdf,docx` **y** `["pdf","docx"]` funcionan.
Reutilizable para `cors_origins`, `allowed_extensions`, `allowed_mime_types`.

---

## 10. Logging

Ubicación `app/shared/logging.py`. Sobre **structlog**.

### Cómo fluye un log

1. Config única al arranque: `main.py::create_app()` llama
   `configure_logging(level, json_logs)`. Instala una cadena de processors.
2. Obtención: `logger = get_logger(__name__)`. *"Never use print."*
3. Emisión estructurada (pares clave-valor, no interpolación):
   ```python
   logger.info("request", method=..., path=..., status=..., duration_ms=...)
   ```
   Primer arg = *evento* (etiqueta estable); resto = contexto estructurado.
4. Processors añaden: contextvars, nivel, timestamp ISO, y **renderizan**:
   `JSONRenderer` si `log_json=True` (prod, para Loki/ELK/Datadog), o
   `ConsoleRenderer(colors=True)` si False (dev, legible).
5. Puente stdlib: `logging.basicConfig(...)` enruta uvicorn y SQLAlchemy por el
   mismo `stdout`.

### ¿Por qué structlog?

Los logs son **datos, no prosa**. `duration_ms=42.3` es un **campo** filtrable/
agregable (`duration_ms > 500`), no una cadena que re-parsear con regex. El mismo
código: salida bonita en dev, JSON en prod, cambiando un flag. En .NET: análogo a
**Serilog** con logging estructurado.

### Cómo agregar contexto

- **Puntual:** kwargs → `logger.info("job_done", job_id=..., dispatched=n)`.
- **Ambiental:** `structlog.contextvars.bind_contextvars(tenant_id=...)`. El
  processor `merge_contextvars` (ya en la cadena) lo inyecta en todos los logs
  subsecuentes de ese contexto async. Ideal para atar `tenant_id`/`request_id`.

---

## 11. Docker

Cuatro piezas: `docker/Dockerfile`, `docker-compose.yml`, `docker/entrypoint.sh`,
red/volúmenes de compose.

### Dockerfile

- Base `ghcr.io/astral-sh/uv:python3.12-bookworm-slim` — con **uv** preinstalado
  (gestor de paquetes de Astral, rapidísimo; = pip/poetry moderno).
- **Capas ordenadas por volatilidad:** primero `pyproject.toml` + `uv.lock` +
  `README.md` + `uv sync` de deps; **luego** `app/`. Cambias código pero no deps →
  Docker reusa la capa de deps cacheada. Builds rápidos.
- `UV_COMPILE_BYTECODE=1`, `PYTHONDONTWRITEBYTECODE=1`, `PYTHONUNBUFFERED=1` —
  precompila bytecode, logs sin buffer (crítico en contenedores).

### entrypoint.sh

```sh
uv run alembic upgrade head || echo "No migrations to apply."
exec uv run uvicorn app.main:app --host ... --port ...
```

Migra antes de arrancar. `exec` reemplaza el shell por uvicorn (señales SIGTERM
llegan directo a la app → shutdown limpio).

### docker-compose.yml — topología

```
┌─────────────────────────────────────────────────────┐
│  compose network (default)                          │
│   api ──depends_on──► postgres (healthcheck)        │
│    │  └─depends_on──► qdrant                         │
│    │  volume: ./storage → /app/storage              │
│    │  extra_hosts: host.docker.internal             │
│    └──────────────────┐                             │
│                       ▼                             │
│              (Ollama en el HOST, fuera de compose)  │
└─────────────────────────────────────────────────────┘
   volumes persistentes: postgres_data, qdrant_data
```

- Tres servicios: `api`, `postgres` (17-alpine), `qdrant`.
- `depends_on` con `condition: service_healthy` para postgres: la API no arranca
  hasta que `pg_isready` pasa. Evita "API arranca antes que la BD".
- Volúmenes: `postgres_data`/`qdrant_data` persisten datos; `./storage:/app/storage`
  (bind mount) → los bytes de documentos quedan en el disco host.
- Red: compose crea red por defecto; servicios se resuelven por nombre
  (`postgres`, `qdrant`) como hostnames.

### Decisión notable: Ollama fuera del compose

`extra_hosts: host.docker.internal:host-gateway` permite que `api` alcance Ollama
en el host vía `LLM_BASE_URL=http://host.docker.internal:11434`. ¿Por qué?
(1) acceso a GPU (frágil en compose); (2) ciclo de vida propio (el modelo pesa
gigas, no debe reiniciarse con cada `docker compose down`). Lo efímero en compose;
lo pesado y stateful fuera.

---

## 12. Testing

Ubicación `tests/`. Config en `pyproject.toml` (`asyncio_mode=auto`, `--cov=app`).

```
tests/
  conftest.py        → fixture `client` (TestClient con lifespan)
  builders.py        → constructores de entidades de prueba
  factories.py       → factories de datos
  fakes.py           → InMemoryStorage, CapturingEventPublisher
  unit/              → UNITARIAS (rápidas, sin I/O)
  integration/       → INTEGRACIÓN (SQLite en memoria)
    conftest.py      → SQLite en memoria + create_all
```

### Unitarias vs integración

- **Unitarias** (`tests/unit/`): una pieza en aislamiento, sin infraestructura.
  Ej.: `test_processing_job.py` prueba la máquina de estados (¿`start()` desde
  estado no-QUEUED lanza `ValidationError`?). `test_metadata.py` prueba validación
  de `KnowledgeMetadata`. Milisegundos.
- **Integración** (`tests/integration/`): varias capas contra infra real pero
  ligera. `conftest.py` monta SQLite en memoria
  (`sqlite+aiosqlite:///:memory:`, `StaticPool`) con `Base.metadata.create_all`.
  Posible solo porque los modelos usan tipos genéricos (sección 7). Fixtures:
  `session`, `document_repo`, `job_repo`, `api_client` (TestClient con BD y
  storage sobrescritos vía `app.dependency_overrides`).

`dependency_overrides` reemplaza `get_database`/`get_storage_provider` por
versiones de test. Es el pago del diseño de DI. En .NET: sustituir servicios en el
`WebApplicationFactory`.

### Cómo escribir una prueba nueva

1. Lógica pura dominio/aplicación → `tests/unit/`. Instancia la clase; pásale los
   fakes de `tests/fakes.py`.
2. Involucra BD/repos/HTTP completo → `tests/integration/`. Usa fixtures
   existentes. Con `asyncio_mode=auto`, tests `async def` corren sin decorador.
3. Reutiliza `builders.py`/`factories.py`.
4. Ejemplo: `CapturingEventPublisher()` → `UploadDocumentUseCase.execute()` →
   assert `events.events` contiene `DocumentUploaded` y que subir el mismo
   contenido dos veces lanza `ConflictError`.

---

## 13. Import Linter

Config en `pyproject.toml`, `[tool.importlinter]`. Guardián automático de la
arquitectura — sustituto de las barreras entre `.csproj`. Corre en `make check`.

### Los 4 contratos

1. **`Clean Architecture layers`** (`layers`): `app.api → app.application →
   app.domain`. Una capa superior importa a una inferior, nunca al revés.
2. **`Domain is framework-free`** (`forbidden`): `app.domain` no puede importar
   `app.api`, `app.application`, `app.infrastructure`, `app.workers`, `fastapi`,
   `sqlalchemy`. Hace cumplir la sección 3.
3. **`Workers know nothing about the web`**: `app.workers` no puede importar
   `app.api` ni `fastapi`.
4. **`Application never imports infrastructure or api`**: fuerza que los use cases
   dependan solo de puertos. El wiring de concretos vive únicamente en
   `api/dependencies.py`.

### ¿Qué pasa si rompes uno?

`make check` (y CI) **falla**. Ejemplo:

```python
# app/application/documents/use_cases/upload_document.py
from app.infrastructure.storage.local_storage import LocalStorageProvider  # ← MAL
```

Funciona en runtime, pero el contrato #4 lo detecta:

```
Broken contract: Application never imports infrastructure or api
  app.application.documents.use_cases.upload_document ->
  app.infrastructure.storage.local_storage
```

Pipeline rojo antes de mergear. El linter convierte una convención frágil en una
invariante verificada.

---

## 14. Flujo del módulo Documents: `POST /documents` → PostgreSQL

```
1. HTTP POST /api/v1/documents (multipart: file, knowledge_space_id; headers tenant/user)

2. routers/documents.py :: upload_document()
      · FastAPI inyecta UploadDocumentUseCaseDep, TenantIdDep, UploadedByDep
      · content = await file.read()
      · construye UploadDocumentInput(...)
      · return await use_case.execute(input)

3. use_cases/upload_document.py :: UploadDocumentUseCase.execute()
   a) validate_upload(...)          [validation.py] → no vacío, ≤ max_size, ext/MIME permitidos → ext
   b) checksum = sha256_hex(content) [shared/hashing.py]
   c) existing = documents.get_by_checksum(tenant_id, checksum)
         → si existe: raise ConflictError ──────► (HTTP 409 en api/errors.py)
   d) document_id = uuid4(); version_id = uuid4(); now = utcnow
   e) storage_key = build_document_version_key(...)  [storage_policy.py]
         → "documents/{tenant}/{yyyy}/{mm}/{document_id}/{version_id}.{ext}"
   f) await storage.save(storage_key, content)   [PUERTO StorageProvider]
         → LocalStorageProvider escribe (asyncio.to_thread)
   g) KnowledgeDocumentVersion(...) + KnowledgeDocument(status=UPLOADED, active_version=version)
   h) await documents.add(document, version)     [PUERTO DocumentRepository]
   i) await events.publish(DocumentUploaded(...)) [PUERTO EventPublisher]
   j) await create_job.execute(CreateProcessingJobInput(job_type=DOCUMENT_INGESTION))
         → verifica "1 job activo por tipo", crea ProcessingJob(QUEUED), jobs.add(),
           publica ProcessingJobCreated
   k) return DocumentView.from_document(document)  [aplana identidad + versión]

4. document_repository.py :: SqlAlchemyDocumentRepository.add(document, version)
        · session.add(_version_to_model(version))  ← Entidad → Modelo ORM
        · session.add(_doc_to_model(document))
        · await session.flush()                    ← empuja SQL (no commit todavía)

5. session.py :: Database.session() (abierto por get_session en el DI)
        · al cerrar el request sin excepción → await session.commit()  ← AQUÍ persiste
        · con excepción → await session.rollback()

6. PostgreSQL: filas en knowledge_documents, knowledge_document_versions, processing_jobs

7. DocumentView → JSON HTTP 201 Created
```

El punto que más confunde: el use case nunca llama `commit()`, hace `flush()`. El
`commit` real ocurre en el paso 5, al salir el `async with` de `get_session` al
terminar el request. **Todo el use case es una transacción atómica**: si
`create_job` lanza por duplicado, el `ConflictError` propaga → rollback → el
documento tampoco se guarda.

Matiz honesto: `storage.save()` (f) escribe a disco **antes** del commit de BD. Si
la transacción hiciera rollback después, el blob quedaría huérfano. Limitación
conocida de coordinar filesystem no-transaccional con BD transaccional; hoy
aceptable (el checksum evita reprocesar duplicados).

---

## 15. Interfaces (puertos) del dominio

Todos `ABC` con `@abstractmethod`. Patrón: dominio define el contrato, infra lo
implementa, aplicación/workers lo consumen. Nadie debe instanciar los adaptadores
fuera del Composition Root.

| Puerto (dominio) | Métodos clave | Implementado por (infra) | Consumido por | Estado |
|---|---|---|---|---|
| **`DocumentRepository`** | add, add_version, get, get_by_checksum, list_documents, list_versions, update | `SqlAlchemyDocumentRepository` | Use cases de documents | ✅ Activo |
| **`ProcessingJobRepository`** | add, get, update, get_active_by_type, list_jobs, claim_queued | `SqlAlchemyProcessingJobRepository` | Use cases de processing + Executor/Dispatcher | ✅ Activo |
| **`PageRepository`** | add_many, list_by_document | — | Pipeline de parsing (futuro) | 🟡 Preparado |
| **`CollectionRepository`** | add, get | — | CRUD de colecciones (futuro) | 🟡 Preparado |
| **`StorageProvider`** | save, load, delete | `LocalStorageProvider` (`InMemoryStorage` tests) | Upload/Process use cases | ✅ Activo (local) |
| **`EventPublisher`** | publish | `LoggingEventPublisher` (`CapturingEventPublisher` tests) | Todos los use cases + Executor | ✅ Activo (log) |
| **`ParserProvider`** | parse(bytes) → ParsedDocument | `PyMuPDFParserProvider` | ProcessDocumentUseCase | 🟡 Scaffolding |
| **`ChunkingStrategy`** | split(text, config) → [TextChunk] | `RecursiveChunkingStrategy` | ProcessDocumentUseCase | 🟡 Scaffolding |
| **`EmbeddingProvider`** | embed_text, embed_batch | `OllamaEmbeddingProvider` | Process/Search/Answer | 🟡 Scaffolding |
| **`VectorRepository`** | upsert, search, delete | `QdrantVectorRepository` | Process/Search/Answer | 🟡 Scaffolding |
| **`LLMProvider`** | complete(messages) → LLMCompletion | `OllamaLLMProvider` | AnswerQuestionUseCase | 🟡 Scaffolding |
| **`ConversationRepository`** | add, get, update | `SqlAlchemyConversationRepository` | AnswerQuestionUseCase | 🟡 Scaffolding |

Por qué existen: cada puerto es **Dependency Inversion Principle**. El negocio
expresa una necesidad ("necesito embeddings") sin comprometerse con una tecnología
(Ollama). Permite testear con dobles, cambiar proveedor sin tocar negocio,
desarrollar en paralelo contra el contrato. Patrón **Ports & Adapters**
(Hexagonal). En C#: `interface` en `Domain`, implementadas en `Infrastructure`.

Abundancia de puertos 🟡: el dominio ya declaró **todos** los contratos que el RAG
necesitará (parse→chunk→embed→index→retrieve→answer). Diseño *contract-first*: el
esqueleto completo existe; las fases futuras solo rellenan cuerpos.

---

## 16. Eventos del dominio

Base `DomainEvent` (`shared/events.py`) — `frozen`, con `event_id` y `occurred_at`
autogenerados. Concretos en `documents/events.py`. Hoy vía `LoggingEventPublisher`.

| Evento | Se dispara cuando… | Publicado desde | Payload |
|---|---|---|---|
| **`DocumentUploaded`** | Se crea un documento con versión 1 | UploadDocumentUseCase | document_id, tenant_id, version_id, version_number, checksum |
| **`DocumentVersionAdded`** | Versión nueva a documento existente | AddDocumentVersionUseCase | document_id, tenant_id, version_id, version_number, checksum |
| **`DocumentDeleted`** | Soft-delete de documento | DeleteDocumentUseCase | document_id, tenant_id |
| **`DocumentMetadataUpdated`** | Actualiza metadata/campos mutables | UpdateDocumentMetadataUseCase | document_id, tenant_id, metadata |
| **`ProcessingJobCreated`** | Se encola un job (→ QUEUED) | CreateProcessingJobUseCase | job_id, document_id, tenant_id, job_type |
| **`ProcessingJobStarted`** | Worker toma el job (→ RUNNING) | WorkerExecutor.execute() | job_id, document_id, tenant_id, worker_name |
| **`ProcessingJobCompleted`** | Job termina con éxito | WorkerExecutor.execute() | job_id, document_id, tenant_id |
| **`ProcessingJobFailed`** | Job falla terminalmente (sin reintentos) | WorkerExecutor._publish_failed() | job_id, document_id, tenant_id, error_message, retry_count |

### ¿Por qué existen?

Hechos de negocio, datos inmutables. Hoy: auditoría/observabilidad (quedan en el
log con `event_id` y timestamp) y desacoplamiento de intención (el use case dice
"esto ocurrió", no "manda un email").

### Cómo podrían evolucionar

`EventPublisher` es un puerto; hoy su adaptador escribe a log. Evolucionar **no
toca dominio ni use cases**:

1. **Message bus real:** `RabbitMQEventPublisher`/`KafkaEventPublisher` + una
   línea en el Composition Root. Los eventos salen a una cola.
2. **Transactional outbox:** `OutboxEventPublisher` que persiste el evento en la
   misma transacción → resuelve "publicar solo si el commit tuvo éxito".
3. **Reacciones internas:** `DispatchingEventPublisher` que enrute a handlers. Ej.:
   `DocumentUploaded` → handler crea el job (invirtiendo el control actual hacia
   arquitectura orientada a eventos pura).
4. **Nuevos eventos de fase:** `PageRendered`, `ChunksGenerated`,
   `EmbeddingsIndexed` (reservados en el docstring). `ProcessingJob.advance()` ya
   tiene los estados intermedios (PARSING, CHUNKING, EMBEDDING…).

`retry_count` en `ProcessingJobFailed` + lógica del `WorkerExecutor` (reintenta si
quedan intentos; solo emite `Failed` al agotarse) ya distinguen "falló pero
reintentará" de "falló definitivamente".

---

## 17. El modelo de datos

### Entidades y razón de ser

- **`KnowledgeDocument`** — Identidad lógica permanente y estable. Sobrevive a los
  cambios de archivo. Guarda tenant, título, source_type, status, metadata tipada,
  puntero a versión activa.
- **`KnowledgeDocumentVersion`** — Archivo físico inmutable. Cada subida = versión
  nueva (nunca sobreescribe). Guarda filename, ext, MIME, size, checksum,
  ubicación, número de versión. El repo nunca hace UPDATE/DELETE de versiones.
- **`KnowledgePage`** — Página de un documento. Dimensiones, rotación, texto
  extraído, ruta a imagen. Nivel intermedio de la trazabilidad + evidencia visual.
  Preparada.
- **`KnowledgeChunk`** — Fragmento recuperable: span de caracteres de una página,
  `bbox` opcional. Unidad central de RAG. Cada chunk se vectoriza en Qdrant; el
  LLM cita chunks y por `Chunk → Page → Document` reconstruye la fuente exacta.
  Existe desde ya, aún sin tabla.
- **`KnowledgeCollection`** — Agrupación de documentos por tenant. Preparada.
- **`ProcessingJob`** — Unidad de trabajo asíncrono. Máquina de estados en el
  dominio; la tabla registra status, priority, retry_count, progress, worker_name,
  timings.

### Relaciones

```
KnowledgeCollection (1) ──< (N) KnowledgeDocument
                                     │ current_version_id ─┐
                                     │                     ▼
      KnowledgeDocument (1) ──< (N) KnowledgeDocumentVersion   [inmutables]
                                     │
      KnowledgeDocument (1) ──< (N) KnowledgePage
                                     │
      KnowledgePage (1) ──< (N) KnowledgeChunk   [→ vector en Qdrant]
                                     │
      KnowledgeDocument (1) ──< (N) ProcessingJob   [FK document_id, ON DELETE CASCADE]
```

FKs a `knowledge_documents` con `ondelete="CASCADE"`. Índices únicos:
`(document_id, version_number)` y `(document_id, page_number)`.

### ¿Por qué así y no de otra forma?

Decisión central: **separar `KnowledgeDocument` de `KnowledgeDocumentVersion`**.
La alternativa "obvia" (una tabla con el archivo inline) es lo que había en la
migración base y el proyecto la **abandonó** en `b7f2c9a4d1e8`. ¿Por qué?

- Un archivo re-subido no debe destruir el anterior → versiones inmutables =
  auditoría y rollback gratis.
- La identidad debe ser estable para trazabilidad (chunks/páginas apuntan a un
  `document_id` que nunca cambia).
- Metadata tipada (`c3d9e1f42a76`) en vez de `dict` genérico → queries
  estructurados futuros.
- Pipeline de jobs rediseñado (`d4e8f1a29b30`): `retry_count`/`progress`/
  `worker_name`/estados de fase → máquina de estados observable.

El modelo evolucionó guiado por necesidades reales (versionado, auditoría,
consultas ricas, observabilidad), cada evolución registrada como migración.

---

## 18. Roadmap técnico

### Estado actual

**Hecho:** ingesta (upload + validación + dedup por checksum + storage local),
versionado inmutable, metadata tipada, soft-delete, listado/paginación, y el
**esqueleto** del pipeline asíncrono (crear job → dispatcher → executor → worker →
máquina de estados → eventos). `NoOpIngestionWorker` completa el job sin trabajo
real, dejando el pipeline cableado y observable de punta a punta.

**Scaffolding:** parsing PDF, chunking, embeddings, Qdrant, LLM, conversaciones, y
los use cases `ProcessDocumentUseCase`, `SemanticSearchUseCase`,
`AnswerQuestionUseCase`.

### Orden de implementación y dependencias

```
FASE A ─ Parsing real
   PyMuPDFParserProvider.parse() → ParsedDocument (texto + páginas)
   Requiere: knowledge_pages poblada, PageRepository implementado.
   Desbloquea: todo lo demás.

FASE B ─ Chunking
   RecursiveChunkingStrategy.split() → TextChunks anclados a página + char span
   Depende de: A. Requiere: tabla de chunks (hoy reservada, sin tabla).

FASE C ─ Embeddings + Vector store (juntas)
   OllamaEmbeddingProvider.embed_batch() → vectores
   QdrantVectorRepository.upsert()/search() → índice
   Depende de: B. Riesgo: requiere Ollama (host) y Qdrant (compose) operativos.

FASE D ─ ProcessDocumentUseCase (orquestación)
   Cablea A→B→C dentro del NoOpIngestionWorker (deja de ser no-op).
   ProcessingJob.advance() emite fases reales (PARSING→CHUNKING→EMBEDDING→INDEXING).

FASE E ─ Search
   SemanticSearchUseCase: embed(query) → vectors.search() → resultados.
   Depende de: C + D.

FASE F ─ Chat / RAG
   AnswerQuestionUseCase: embed → search → prompt con contexto →
   LLMProvider.complete() → persistir en ConversationRepository.
   Depende de: E + LLMProvider + ConversationRepository reales.
```

Grafo: **A → B → C → D → {E → F}**. A raíz crítica; F hoja que corona el RAG.

### Riesgos técnicos

1. **Coordinación storage/BD no transaccional.** `storage.save()` antes del commit.
   Al escalar (S3, más pasos): patrón outbox o compensación para blobs huérfanos.
2. **Dispatcher in-process y one-shot.** `run_worker.py` ejecuta un batch y
   termina. Producción: scheduler/loop o reemplazar `JobDispatcher` por Celery/
   broker (el docstring lo anticipa). El diseño lo permite sin tocar dominio.
3. **`claim_queued` sin lock.** Falta `SELECT ... FOR UPDATE SKIP LOCKED`. Con
   varios workers concurrentes, dos podrían reclamar el mismo job.
4. **Tabla de chunks inexistente.** Fase B la necesita. Migración pendiente.
5. **Dependencias externas de IA.** Ollama (GPU, host) y Qdrant: latencia y modos
   de fallo nuevos. Afinar `max_retries`, timeouts de `httpx`, backpressure.
6. **Coste de embeddings/LLM.** Medir throughput contra `dispatch_batch_size`.

Buena noticia: **el roadmap es rellenar cuerpos de métodos, no re-arquitecturar.**
Todos los puertos, el pipeline de jobs, la máquina de estados, los eventos y el DI
ya existen. Cada fase: "implementa este adaptador, cablea este use case, añade esta
migración" — y el `import-linter` + los tests avisan si te sales del carril.

---

## Cierre — mapa mental

- **Una regla:** las dependencias apuntan al dominio; el dominio no apunta a nada.
  El `import-linter` la vigila.
- **Cuatro capas:** `domain` (qué es el negocio, puro), `application` (casos de uso),
  `infrastructure` (cómo, tecnología concreta), `api` (frontera HTTP + único wiring).
- **Puertos y adaptadores:** el dominio declara `ABC`s; la infra las implementa; el
  Composition Root (`api/dependencies.py`) las ata; FastAPI las inyecta por request.
- **Transacción = request:** el commit lo hace el context manager de la sesión, no
  los use cases.
- **Pipeline asíncrono ya cableado**, con IA como scaffolding contract-first.
