# Guia de despliegue con Docker

Esta guia explica como levantar OpenPiar usando Docker Compose en cualquier VPS o servidor con Docker instalado. Al terminar tendras tres contenedores corriendo: PostgreSQL, el backend FastAPI y el frontend servido por Nginx.

---

## Requisitos previos

- Docker Engine 24+ y Docker Compose v2 instalados en el servidor.
- Un dominio apuntando al servidor (opcional, para produccion con HTTPS).
- Una API key de Google Gemini ([aistudio.google.com/apikey](https://aistudio.google.com/apikey)), opcional: tambien puede ingresarse desde el asistente de configuracion.

Si tu VPS no tiene Docker, instalalo con:

```bash
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
newgrp docker
docker compose version
```

---

## 1. Clonar el proyecto

```bash
git clone https://github.com/Dramoscuello/openpiar.git /opt/openpiar
cd /opt/openpiar
```

---

## 2. Configurar las variables de entorno

Docker solo necesita **un archivo `.env` en la raíz**:

```bash
cp .env.example .env
nano .env
```

### En `.env` (raíz) completa:

| Variable | Descripcion |
|----------|-------------|
| `DB_USER` | Usuario de PostgreSQL (ej: `openpiar_user`) |
| `DB_PASSWORD` | Contrasena de PostgreSQL |
| `DB_NAME` | Nombre de la base de datos (ej: `openpiar_db`) |
| `SECRET_KEY` | Firma JWT, generala con `openssl rand -hex 32` |
| `GEMINI_API_KEY` | **Opcional.** Tu API key de Google Gemini |
| `CORS_ORIGINS` | Dominio o IP desde donde se accede (ej: `https://openpiar.mi-colegio.edu.co`). Con Nginx sirviendo la interfaz y la API en el mismo origen no suele ser necesario cambiarlo |

`DB_HOST` y `DB_PORT` no se configuran: `docker-compose.yml` los fija automaticamente a `db` y `5432` (nombres internos de la red Docker). El resto de variables (`APP_ENV`, `SHOW_DOCS`, `GEMINI_MODEL`, `FRONTEND_PORT`) tienen valores por defecto razonables.

> **Para desarrollo local sin Docker** (ejecutando `uvicorn` directamente) el archivo es `backend/.env`; puedes copiarlo de `backend/.env.example`. El contenedor **no** usa `backend/.env`.

### Sobre la API key de Gemini

No es obligatorio definirla en `.env`:

1. Puedes ingresarla durante el **asistente de configuración inicial** (se guarda en la base de datos).
2. O después, como directivo, en **Gestion Escolar -> Configuracion**.
3. La clave guardada en la base de datos tiene **prioridad** sobre `GEMINI_API_KEY` del `.env` (que es solo un respaldo para desarrollo).

---

## 3. Levantar los servicios

```bash
docker compose up -d
```

La primera vez tomara unos minutos porque construye las imagenes del backend y frontend. Al arrancar, el backend:

1. Espera a que PostgreSQL este listo.
2. Prepara el esquema de la base de datos: en una instalacion nueva lo crea desde los modelos y marca Alembic; si la base ya existe, aplica las migraciones pendientes (`alembic upgrade head`).
3. Siembra el curriculo nacional (DBA y EBC) si aun no esta.
4. Inicia Uvicorn en el puerto 8000.

Para ver los logs mientras arranca:

```bash
docker compose logs -f
```

Cuando veas `Uvicorn running on http://0.0.0.0:8000`, el sistema esta listo.

---

## 4. Acceder a la aplicacion

Abre `http://<ip-o-dominio-del-servidor>` en tu navegador. El asistente de configuracion inicial te guiara para:

1. Registrar los datos de tu institucion.
2. Ingresar la API key de Gemini (opcional; tambien puedes configurarla despues).
3. Subir el PDF del PEI; la IA extrae el modelo pedagogico.
4. Crear la cuenta de administrador.

Una vez completado, OpenPiar queda operativo.

---

## 5. Configurar HTTPS (produccion)

Para exponer la aplicacion con SSL, agrega un reverse proxy delante. Dos enfoques comunes:

### Opcion A: Nginx en el host + Certbot

Instala nginx y certbot en el VPS (no dentro de Docker) y crea un proxy hacia `localhost:80`:

```bash
sudo apt install -y nginx certbot python3-certbot-nginx
```

Crea `/etc/nginx/sites-available/openpiar`:

```nginx
server {
    listen 80;
    server_name openpiar.mi-colegio.edu.co;

    # Subidas (PEI, evidencias, importacion .openpiar)
    client_max_body_size 60m;

    location / {
        proxy_pass http://127.0.0.1:80;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 120s;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/openpiar /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
sudo certbot --nginx -d openpiar.mi-colegio.edu.co
```

**Importante:** cambia `CORS_ORIGINS` en tu `backend/.env` al dominio con `https://` y recrea el backend:

```bash
docker compose up -d --force-recreate backend
```

### Opcion B: Cloudflare Tunnel

Si usas Cloudflare como DNS, podes usar `cloudflared tunnel` en lugar de abrir puertos. Esto te da SSL automatico sin certbot.

---

## 6. Comandos utiles

| Accion | Comando |
|--------|---------|
| Levantar servicios | `docker compose up -d` |
| Detener servicios | `docker compose down` |
| Ver logs | `docker compose logs -f` |
| Ver logs de un servicio | `docker compose logs -f backend` |
| Reiniciar todo | `docker compose restart` |
| Reconstruir imagenes | `docker compose up -d --build` |
| Entrar al contenedor del backend | `docker compose exec backend bash` |
| Estado de los contenedores | `docker compose ps` |

---

## 7. Actualizar la aplicacion

Cuando haya cambios en el repositorio:

```bash
cd /opt/openpiar
git pull origin main
docker compose up -d --build
```

Esto reconstruye las imagenes del backend y frontend con el codigo nuevo y recrea los contenedores. Los datos de PostgreSQL se conservan en el volumen `postgres_data`.

Las **migraciones de Alembic se aplican automaticamente** al arrancar el backend, asi que no hay pasos manuales.

> Si venis de una instalacion muy antigua cuya base de datos se creo sin Alembic (sin tabla `alembic_version`), el arranque fallara al aplicar migraciones. En ese caso marca la base como al dia una sola vez:
>
> ```bash
> docker compose exec backend python -m alembic stamp head
> docker compose restart backend
> ```
>
> Haz un respaldo antes (ver seccion 8).

---

## 8. Respaldar la base de datos

```bash
docker compose exec db pg_dump -U openpiar_user openpiar_db | gzip > backup_$(date +%Y%m%d).sql.gz
```

Para restaurar:

```bash
gunzip -c backup_20250101.sql.gz | docker compose exec -T db psql -U openpiar_user openpiar_db
```

Programa el respaldo con cron en el host:

```bash
crontab -e
```

```
0 2 * * * docker compose -f /opt/openpiar/docker-compose.yml exec -T db pg_dump -U openpiar_user openpiar_db | gzip > /opt/backups/openpiar_$(date +\%Y\%m\%d).sql.gz
```

---

## 9. Solucion de problemas

### El frontend carga pero la API no responde

Revisa que el backend este corriendo:

```bash
docker compose ps backend
docker compose logs backend --tail 50
```

### Error de conexion a PostgreSQL

El backend espera a que PostgreSQL responda antes de arrancar (reintenta cada 2 segundos). Si falla, verifica:

```bash
docker compose logs db
docker compose ps db
```

### Falla la preparacion del esquema

El backend ejecuta `scripts/init_db.py` en cada arranque:

- Base **nueva** (sin tablas): la crea desde los modelos y la marca en la ultima revision de Alembic.
- Base **existente y versionada**: aplica `alembic upgrade head`.
- Base **con tablas pero sin `alembic_version`** (instalacion antigua): el contenedor se detiene e indica el paso a seguir. Tras respaldar, marca la revision que corresponda:

```bash
docker compose exec backend python -m alembic stamp head
docker compose restart backend
```

### El seed del curriculo falla

El entrypoint del backend ejecuta `seed_curriculum.py` en cada arranque. Es idempotente, asi que si falla la primera vez, simplemente reinicia:

```bash
docker compose restart backend
```

### Error 412 Precondition Failed

El asistente de configuracion inicial no se ha completado. Accede a la raiz del sitio y completa el wizard.

### La IA no genera sugerencias

- Verifica que la clave de Gemini este configurada en **Gestion Escolar -> Configuracion** (se guarda en la base de datos y tiene prioridad).
- Como respaldo de desarrollo, tambien puede estar en `GEMINI_API_KEY` del `.env` raiz.
- Asegurate de que sea una clave valida con creditos disponibles.
- Reinicia el backend: `docker compose restart backend`.

### Cambiar el puerto del frontend

Agrega `FRONTEND_PORT` al archivo `.env` de la raiz. Por ejemplo, para usar el puerto 8080:

```
FRONTEND_PORT=8080
```

Luego:

```bash
docker compose up -d
```

---

## 10. Probar en otro equipo (checklist)

1. Instala Docker Engine 24+ con Compose v2.
2. Clona el repositorio: `git clone <repo> openpiar && cd openpiar`.
3. Crea el archivo de entorno: `cp .env.example .env`.
   - Define `DB_PASSWORD` y `SECRET_KEY` (obligatorias). `openssl rand -hex 32` para la segunda.
   - `GEMINI_API_KEY` puede quedar vacia: se configura en el asistente.
4. Valida la configuracion de Compose: `docker compose config`.
5. Levanta todo: `docker compose up -d --build`.
6. Sigue los logs: `docker compose logs -f backend`. Debes ver las migraciones, el seed y `Uvicorn running`.
7. Abre `http://<ip-o-dominio>` y completa el wizard (datos de la institucion, PEI y la API key de Gemini).
8. Verifica: login, `GET /api/v1/health`, dashboard y generacion de PDF.

Notas:

- Los datos viven en los volumenes `postgres_data` (base de datos) y `backend_uploads` (evidencias). No los borres si quieres conservar informacion.
- Si cambias `FRONTEND_PORT`, usa ese puerto en el paso 7.
- Las imagenes del backend/frontend se construyen sin `.venv`, `node_modules`, `.env` ni uploads locales (ver `.dockerignore`).

---

## 11. Personalizacion avanzada

### Aumentar workers del backend

Edita `backend/docker-entrypoint.sh` y modifica la linea de Uvicorn:

```bash
exec python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Usar una version especifica de PostgreSQL

Cambia la imagen en `docker-compose.yml`:

```yaml
db:
  image: postgres:16-alpine   # o postgres:17-alpine, etc.
```

### Exponer el backend directamente (solo desarrollo)

Modifica `docker-compose.yml` para mapear el puerto 8000:

```yaml
backend:
  ports:
    - "8000:8000"
```

Esto permite acceder a `http://localhost:8000/docs` para ver la documentacion de la API (si `SHOW_DOCS=True`).
