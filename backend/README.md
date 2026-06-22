# OpenPiar — Backend

API del Gestor de PIARs Comunitario, construida con **FastAPI + SQLAlchemy 2.0 async + Alembic + PostgreSQL**.

## Arquitectura

Hexagonal + DDD con capas estrictas:

```
domain/          ← Núcleo puro (sin frameworks)
use_cases/       ← Orquestación de negocio
adapters/        ← Implementaciones concretas (PostgreSQL, Gemini)
entrypoints/api/ ← Borde HTTP (FastAPI)
```

## Setup rápido

### 1. Prerrequisitos

- Python 3.11+
- PostgreSQL 14+
- (Opcional) API Key de Google Gemini

### 2. Instalación

```bash
cd backend

# Crear entorno virtual
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt
```

### 3. Configurar variables de entorno

```bash
cp .env.example .env
# Editar .env con tus credenciales de PostgreSQL y Gemini
```

Variables mínimas para desarrollo:

```env
DB_HOST=localhost
DB_PORT=5432
DB_USER=openpiar_user
DB_PASSWORD=mi_password_segura
DB_NAME=openpiar_db
SECRET_KEY=clave_secreta_muy_larga_y_aleatoria
GEMINI_API_KEY=tu_api_key_de_gemini   # Opcional en desarrollo
```

### 4. Crear base de datos y ejecutar migraciones

```sql
-- En PostgreSQL:
CREATE USER openpiar_user WITH PASSWORD 'mi_password_segura';
CREATE DATABASE openpiar_db OWNER openpiar_user;
```

```bash
# Aplicar migraciones (crea todas las 15 tablas)
alembic upgrade head
```

### 5. Arrancar el servidor

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

API disponible en: http://localhost:8000
Documentación Swagger: http://localhost:8000/docs

## Flujo de configuración inicial (Setup Wizard)

La primera vez que el frontend carga, consulta `GET /api/v1/setup/status`.
Si `setup_completado: false`, presenta el asistente:

1. `POST /api/v1/setup/test-db` — Prueba la conexión a PostgreSQL
2. `POST /api/v1/setup/configure` — Datos del colegio + admin inicial
3. `POST /api/v1/setup/upload-pei` — PDF del PEI (opcional, extracción con IA)

## Ejecutar tests

```bash
# Tests unitarios (sin BD — repositorios en memoria)
pytest tests/ -v

# Con cobertura
pytest tests/ --cov=app --cov-report=term-missing
```

## Ingesta de currículum DBA/EBC

```bash
# 1. Colocar PDFs en /dba/ y /ebc/ (carpetas del proyecto raíz)
# 2. Extraer y generar fixtures JSON
python scripts/ingest_curriculum.py

# 3. Cargar a PostgreSQL
python scripts/seed_curriculum.py
```

## Estructura de archivos

```
backend/
├── app/
│   ├── domain/           # Value Objects, Entidades, Puertos (contratos)
│   ├── use_cases/        # Casos de uso (lógica de negocio)
│   ├── adapters/         # PostgreSQL, Gemini API
│   ├── entrypoints/api/  # Endpoints FastAPI
│   ├── core/             # Config, Security, Exceptions
│   └── fixtures/         # JSONs de DBA/EBC (currículum MEN)
├── alembic/              # Migraciones de BD
├── scripts/              # Ingesta y seeding de datos
├── tests/                # Tests unitarios
├── requirements.txt
├── alembic.ini
└── .env.example
```

## Licencia

GNU General Public License v3.0 — ver [LICENSE](../LICENSE)
