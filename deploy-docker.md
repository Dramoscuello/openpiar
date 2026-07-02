# Guia de despliegue con Docker

Esta guia explica como levantar OpenPiar usando Docker Compose en cualquier VPS o servidor con Docker instalado. Al terminar tendras tres contenedores corriendo: PostgreSQL, el backend FastAPI y el frontend servido por Nginx.

---

## Requisitos previos

- Docker Engine 24+ y Docker Compose v2 instalados en el servidor.
- Un dominio apuntando al servidor (opcional, para produccion con HTTPS).
- Una API key de Google Gemini ([aistudio.google.com/apikey](https://aistudio.google.com/apikey)).

Si tu VPS no tiene Docker, instalalo con:

```bash
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
# Cierra sesion y vuelve a entrar para que el grupo surta efecto
```

---

## 1. Clonar el proyecto

```bash
git clone https://github.com/tu-usuario/OpenPiar.git /opt/openpiar
cd /opt/openpiar
```

---

## 2. Configurar las variables de entorno

OpenPiar usa dos archivos de entorno:

```bash
# 1. Backend (todas las variables de la aplicacion)
cp backend/.env.example backend/.env
nano backend/.env

# 2. Docker Compose (solo credenciales de PostgreSQL para el contenedor de BD)
cp .env.example .env
nano .env
```

### En `backend/.env` completa:

| Variable | Descripcion |
|----------|-------------|
| `SECRET_KEY` | Generala con `openssl rand -hex 32` |
| `DB_USER` | Usuario de PostgreSQL (ej: `openpiar_user`) |
| `DB_PASSWORD` | Contrasena de PostgreSQL |
| `DB_NAME` | Nombre de la base de datos (ej: `openpiar_db`) |
| `GEMINI_API_KEY` | Tu API key de Google Gemini |
| `CORS_ORIGINS` | Dominio desde donde se accede (ej: `https://openpiar.mi-colegio.edu.co`) |

El resto de variables (`APP_ENV`, `SHOW_DOCS`, `GEMINI_MODEL`, etc.) tienen valores por defecto razonables.

### En `.env` (raiz) completa:

Las mismas credenciales de PostgreSQL que pusiste en `backend/.env`:

```bash
DB_USER=openpiar_user
DB_PASSWORD=la_misma_contrasena
DB_NAME=openpiar_db
```

Esto es necesario para que el contenedor de PostgreSQL se cree con las mismas credenciales que espera el backend. El `DB_HOST` y `DB_PORT` no se configuran: el `docker-compose.yml` los fija automaticamente a `db` y `5432` (nombres internos de la red Docker).

---

## 3. Levantar los servicios

```bash
docker compose up -d
```

La primera vez tomara unos minutos porque construye las imagenes del backend y frontend. El backend espera automaticamente a que PostgreSQL este listo y siembra el curriculo nacional (DBA y EBC) en la base de datos.

Para ver los logs mientras arranca:

```bash
docker compose logs -f
```

Cuando veas `Uvicorn running on http://0.0.0.0:8000`, el sistema esta listo.

---

## 4. Acceder a la aplicacion

Abre `http://<ip-o-dominio-del-servidor>` en tu navegador. El asistente de configuracion inicial te guiara para:

1. Registrar los datos de tu institucion.
2. Subir el PDF del PEI.
3. Crear la cuenta de administrador.

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

    location / {
        proxy_pass http://127.0.0.1:80;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
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

Si la actualizacion incluye migraciones de Alembic, ejecutalas manualmente:

```bash
docker compose exec backend python -m alembic upgrade head
docker compose restart backend
```

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

El backend espera hasta 10 intentos del healthcheck de PostgreSQL antes de arrancar. Si falla, verifica:

```bash
docker compose logs db
docker compose ps db
```

### El seed del curriculo falla

El entrypoint del backend ejecuta `seed_curriculum.py` en cada arranque. Es idempotente, asi que si falla la primera vez, simplemente reinicia:

```bash
docker compose restart backend
```

### Error 412 Precondition Failed

El asistente de configuracion inicial no se ha completado. Accede a la raiz del sitio y completa el wizard.

### La IA no genera sugerencias

- Verifica que `GEMINI_API_KEY` este configurada en `backend/.env`.
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

## 10. Personalizacion avanzada

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
