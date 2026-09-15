# OpenPiar — Guía para Agentes

## Identidad del Proyecto
Plataforma de código abierto para colegios colombianos que gestiona el **PIAR** (Plan Individual de Ajustes Razonables) de estudiantes con discapacidad y Trastornos Específicos del Aprendizaje (TEAp). Se rige por el **Decreto 1421 de 2017**, la **Ley 2216 de 2022**, el **Decreto 1860 de 1994** y el marco **DUA** (Diseño Universal para el Aprendizaje). Licencia **GPL-3.0**.

## Arquitectura

**Backend:** Hexagonal + DDD con FastAPI. Separación estricta de capas — `domain` NUNCA importa de `adapters` ni de `entrypoints`.

```
backend/app/
├── domain/               # Reglas de negocio puras
│   ├── entities/         # Usuario, Estudiante, Piar (raíz de agregado), AuditoriaCambio
│   ├── value_objects/    # Email, CodigoDANE, NIT, NumeroDocumento, Rol
│   └── ports/            # Interfaces (IUsuarioRepository, IEstudianteRepository, IPiarRepository, IAgentePedagogico, IAuditoriaRepository)
├── use_cases/            # Orquesta entidades + puertos (auth/, estudiantes/, piars/)
├── adapters/             # Implementaciones concretas
│   ├── db/postgres/      # PostgresUsuarioRepository, PostgresEstudianteRepository, PostgresAuditoriaRepository
│   └── ai/gemini_adapter.py
├── entrypoints/api/      # FastAPI
│   ├── v1/endpoints/     # Routers por dominio + v1/router.py
│   ├── dependencies.py   # Inyección de repos, auth, roles
│   ├── middleware.py     # Setup Guard
│   └── schemas.py
├── core/                 # config, security (JWT+bcrypt), exceptions, pdf_generator, notification_service, portable_exporter
└── fixtures/             # JSON estático (DBA, EBC, areas_asignaturas)
```

- **Puertos** (interfaces abstractas) en `domain/ports/` — los repos concretos se inyectan vía `Depends()` en `entrypoints/api/dependencies.py`.
- **Nota:** `IPiarRepository` **no tiene adaptador Postgres**. La persistencia PIAR se hace directamente con SQLAlchemy en `entrypoints/api/v1/endpoints/piars.py`.
- **IA:** `adapters/ai/gemini_adapter.py` implementa `IAgentePedagogico`, pero `piars.py` también llama a Gemini directamente con dos SDKs distintos (`google-generativeai` legacy y `google-genai`).
- **Tests** usan repositorios in-memory — cero BD/red en tests unitarios.

**Frontend:** Vue 3 (Composition API) + Vite + Pinia + Tailwind CSS 4 + vue-router + Shepherd.js (tour de onboarding).

## Comandos

### Backend (workdir: `backend/`)
```bash
# Instalar deps (usa .venv)
.venv/bin/pip install -r requirements.txt

# Servidor dev (puerto 8000, Swagger en /docs)
.venv/bin/python -m uvicorn app.main:app --reload --port 8000

# Tests (async, repos in-memory)
.venv/bin/python -m pytest tests/ -v

# Test específico
.venv/bin/python -m pytest tests/test_domain.py -v

# Sembrar currículum (DBA + EBC en PostgreSQL) — una vez, offline
.venv/bin/python scripts/seed_curriculum.py

# Ingesta de PDFs oficiales MEN → fixtures JSON (requiere OPENAI_API_KEY y `openai`, no incluido en requirements.txt)
.venv/bin/python scripts/ingest_curriculum.py
.venv/bin/python scripts/ingest_extra_curriculum.py

# Migraciones Alembic
.venv/bin/python -m alembic upgrade head        # aplicar todas
.venv/bin/python -m alembic revision --autogenerate -m "descripcion"  # nueva migración
```

### Frontend (workdir: `frontend/`)
```bash
npm install
npm run dev         # Vite dev server :5173, proxy /api → localhost:8000
npm run build       # type-check + build (en paralelo)
npm run type-check  # vue-tsc --build
npm test            # vitest run
npm run preview     # servir build de producción
```

### Docker (raíz del repo)
```bash
cp .env.example .env        # credenciales DB para Compose
docker compose up -d        # db (Postgres 16) + backend + frontend (Nginx)
docker compose logs -f backend
docker compose down
```

## Configuración y Entorno

Copiar `backend/.env.example` → `backend/.env`. Variables relevantes:
- `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME` (PostgreSQL vía asyncpg; `DATABASE_URL` se ensambla automáticamente)
- `SECRET_KEY` (firma JWT; generar con `openssl rand -hex 32`)
- `ACCESS_TOKEN_EXPIRE_MINUTES` (default 720)
- `GEMINI_API_KEY` y `GEMINI_MODEL` (default en código: `gemini-3.1-flash-lite`)
- `OPENAI_API_KEY` (solo para scripts de ingesta de currículum)
- `APP_ENV`, `SHOW_DOCS`, `CORS_ORIGINS`

Para Docker Compose, copiar `.env.example` (raíz) → `.env`: `DB_USER`, `DB_PASSWORD`, `DB_NAME`, `FRONTEND_PORT`.

El backend auto-crea las tablas al arrancar vía `lifespan` (`Base.metadata.create_all`), por lo que en dev no hace falta migración explícita.

## Flujo de Arranque

1. Backend inicia → `lifespan` crea tablas e **inicia un loop de notificaciones cada 6 h** (`core/notification_service.py::ejecutar_notificaciones_periodicas`, con advisory lock de PostgreSQL anti-duplicados). Ver `main.py:66-75`.
2. **Middleware Setup Guard** (`entrypoints/api/middleware.py:33`): retorna **412** en todas las rutas `/api/*` hasta que `configuracion_sistema.setup_completado = TRUE`.
   - Rutas exentas: `/api/v1/setup/*`, `/api/v1/familia`, `/api/v1/health`, `/docs`, `/redoc`, `/openapi.json`, `/favicon.ico`.
3. Guard del router frontend (`frontend/src/router/index.ts:79`) redirige a `/setup` hasta completar la configuración.
4. Tras el setup: login → JWT en `localStorage` bajo `openpiar_token` → header `Authorization` en cada petición.

## API Endpoints (v1)

Todos bajo el prefijo `/api/v1` (registrado en `main.py:242`).

| Prefijo | Archivo | Propósito / Acceso |
|---------|---------|--------------------|
| `/api/v1/setup` | `setup.py` | Wizard: `status`, `test-db`, `configure` (crea directivo admin), `upload-pei`. Público |
| `/api/v1/auth` | `auth.py` | `login`, `me`, `change-password`, `tour-completado`. Público / autenticado |
| `/api/v1/estudiantes` | `estudiantes.py` | CRUD Anexo 1 + subrecursos `salud`, `hogar`, `trayectoria`, `matricula` + export/import `.openpiar`. Escritura: directivo o director de grupo |
| `/api/v1/curriculum` | `curriculum.py` | Búsqueda DBA (`/dba`) y EBC (`/ebc`). Autenticado |
| `/api/v1/gestion` | `gestion_escolar.py` | Sedes, docentes, directivos, áreas, asignaturas, grados, grupos, carga académica, periodos. Mutaciones: directivo |
| `/api/v1/piars` | `piars.py` | PIAR: CRUD, ajustes, generación IA, PMI, completitud, finalizar/reabrir/versionar, acta Anexo 3, evidencias, historial de auditoría, PDF. Autenticado |
| `/api/v1/dashboard` | `dashboard.py` | Estadísticas institucionales agregadas. Autenticado |
| `/api/v1/directorio` | `directorio.py` | Directorio de acudientes. Directivo o director de grupo |
| `/api/v1/familia` | `familia.py` | Acceso público por código (`/familia/{codigo}`): consulta PIAR, firma y acta PDF. **Sin JWT** |
| `/api/v1/notificaciones` | `notificaciones.py` | Notificaciones in-app del usuario. Autenticado |
| `/api/v1/configuracion` | `configuracion.py` | Lectura/edición de configuración institucional. Directivo |
| `/api/v1/health` | `main.py` | Health check (en `main.py:223`) |

## Convenciones Clave

- **Todos los archivos fuente** deben comenzar con el header de copyright GPL-3.0: `# Copyright (c) 2026 OpenPiar Contributors — GPL-3.0`.
- **Excepciones de dominio** (`core/exceptions.py`) se mapean a códigos HTTP con handlers en `main.py`. Lanzar excepciones de dominio desde use_cases; nunca `HTTPException` desde `domain/` o `use_cases/`.
- **Roles:** `directivo`, `docente_aula`, `docente_apoyo`, `orientador` (`value_objects.Rol`). `require_directivo` en `entrypoints/api/dependencies.py:85` protege endpoints admin. El "director de grupo" es independiente del rol: se determina por `GrupoORM.director_id`.
- **Autorización por entidad:** escritura de estudiantes = directivo o director de grupo; creación de PIAR = director de grupo o directivo; cobertura de asignaturas = docente asignado a la carga académica.
- **Pydantic v2** en todo el proyecto — usar `model_validator` y `computed_field` (ver `core/config.py`).
- **Frontend/estado:** 5 stores Pinia en `src/stores/` — `auth.ts`, `dashboard.ts`, `piar.ts`, `students.ts`, `tour.ts`. Persistencia: `openpiar_token` (JWT), `openpiar_student_draft` (borrador), `theme` (modo oscuro).
- **Cliente HTTP frontend:** no hay axios ni cliente central con interceptores. Se usa `fetch` nativo con header `Authorization: Bearer`; el helper `src/api/auth.ts::apiFetch` solo cubre auth/setup.
- **CSS:** Tailwind CSS 4 (`@tailwindcss/vite`, configuración CSS-first en `src/assets/main.css`). Sin `tailwind.config.js`.
- **Markdown en git:** la whitelist de `.gitignore` permite `readme.md`, `README.md`, `deploy.md`, `deploy-docker.md` y `AGENTS.md`. El resto de `.md` queda fuera de git (varios son documentos legales o notas locales).

## Restricciones Importantes

- **PostgreSQL** es la única base de datos de producción. La arquitectura hexagonal *permite* adaptadores SQLite, pero no existen.
- El **Setup Wizard** debe ejecutarse antes de cualquier otra interacción con la API — aplicado en middleware y en el router del frontend.
- Los datos curriculares (DBA/EBC) se precargan como fixtures JSON; **nunca** se descargan de internet en runtime.
- El panel de **familia** es de acceso público por código (`codigo_acceso_familia`), sin autenticación JWT.
- El export/import portable `.openpiar` usa cifrado **AES-256-GCM** con PBKDF2-HMAC-SHA256 (`core/portable_exporter.py`).
- La IA usa Gemini (dos SDKs); no hay adaptador Ollama implementado.

## Deployment

Dos rutas documentadas:
- **Docker Compose** (`docker-compose.yml`): servicios `db` (Postgres 16), `backend` (FastAPI/Uvicorn) y `frontend` (Nginx sirviendo `frontend/dist` y proxy a la API). Ver `deploy-docker.md`.
- **VPS tradicional** (Nginx + systemd + PostgreSQL): ver `deploy.md`.

## Testing

- **Backend:** `pytest` (config en `backend/pyproject.toml`, `asyncio_mode = "auto"`). Usa repositorios in-memory, sin PostgreSQL ni Gemini.
  - `tests/test_domain.py` — value objects, entidades, casos de uso de auth/estudiantes.
  - `tests/test_piar_workflow.py` — reglas de completitud, campos obligatorios y versionado.
  - `tests/test_piar_api_contracts.py` — contratos OpenAPI y lógica de permisos/visibilidad.
  - `tests/test_pdf_oficial.py` — regresión de PDFs oficiales (con `pypdf`/`pdfplumber`).
- **Frontend:** Vitest (`vite.config.ts`, entorno `jsdom`, specs `src/**/*.spec.ts`); ejecutar con `npm test`.
  - `src/components/piar/PiarWizard.spec.ts` y `src/composables/usePiarVisibility.spec.ts`.

## Features Ocultas

Dos funcionalidades están implementadas pero desactivadas por flags en `frontend/src/views/PiarView.vue`:
- `ajusteRatingEnabled` → calificación de ajustes (1–5) y comentario.
- `curriculumSearchEnabled` → buscador de mallas DBA/EBC y contexto curricular automático.

Cambiar a `true` para reactivarlas. Detalle local en `caracteristicas_ocultas.md` (fuera de git).

## Flujo Spec-driven

El desarrollo de features sigue especificaciones versionadas en el repo:
- `spec/constitution/roadmap.md` — principios y roadmap de producto.
- `spec/features/feature 001/`, `spec/features/feature 002/`, `spec/features/feature 003/` y `spec/features/feature 004/` — `plan.md` y `tasks.md` (planificación por feature).

## Referencias

- `roadmap.md` — arquitectura de software, esquema de BD y decisiones de stack
- `pattern_architecture.md` — justificación de hexagonal + DDD y estructura de directorios
- `ingesta_dba_ebc.md` — pipeline de ingesta del currículum
- `deploy.md` / `deploy-docker.md` — guías de despliegue
- `CONTRIBUTING.md`, `SECURITY.md`, `CODE_OF_CONDUCT.md` — contribución y gobierno
- `readme.md` — visión general para el usuario (español)
- `spec/` — constitución y especificaciones por feature
