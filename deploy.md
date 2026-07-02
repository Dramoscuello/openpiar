# Guia de despliegue en VPS (instalacion tradicional)

> Si preferis usar Docker, consulta [deploy-docker.md](deploy-docker.md) para un despliegue simplificado con Docker Compose.

Esta guia describe paso a paso como instalar y poner en produccion OpenPiar en un VPS con Ubuntu 24.04 LTS. Se asume que tienes acceso root o un usuario con `sudo` y un dominio apuntando al servidor (ej: `openpiar.mi-colegio.edu.co`).

---

## Arquitectura objetivo

```
Usuario → Nginx (puerto 80/443)
            ├── /api/*       → proxy → Uvicorn (127.0.0.1:8000)
            └── resto        → archivos estaticos (frontend/dist/)
```

- **Nginx** sirve el frontend compilado y redirige las peticiones de la API al backend.
- **Uvicorn** corre como servicio de systemd, reiniciandose automaticamente si falla.
- **PostgreSQL** almacena todos los datos de la aplicacion.

---

## 1. Preparar el sistema

Actualiza los paquetes e instala las dependencias base:

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3.13 python3.13-venv python3.13-dev \
                    postgresql postgresql-client \
                    nginx certbot python3-certbot-nginx \
                    git curl build-essential libpq-dev
```

Verifica las versiones:

```bash
python3.13 --version   # Debe mostrar Python 3.13.x
node --version         # Si no esta instalado, sigue abajo
```

### Instalar Node.js 22

```bash
curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
sudo apt install -y nodejs
node --version         # Debe mostrar v22.x
```

---

## 2. Configurar PostgreSQL

Inicia el servicio y crea la base de datos con su usuario:

```bash
sudo systemctl enable postgresql
sudo systemctl start postgresql

sudo -u postgres psql <<EOF
CREATE USER openpiar_user WITH PASSWORD 'TU_CONTRASENA_SEGURA';
CREATE DATABASE openpiar_db OWNER openpiar_user;
GRANT ALL PRIVILEGES ON DATABASE openpiar_db TO openpiar_user;
\c openpiar_db
GRANT ALL ON SCHEMA public TO openpiar_user;
EOF
```

Guarda esa contrasena. La necesitaras en el archivo `.env`.

---

## 3. Clonar el proyecto

```bash
sudo mkdir -p /opt/openpiar
sudo chown $USER:$USER /opt/openpiar
git clone https://github.com/tu-usuario/OpenPiar.git /opt/openpiar
cd /opt/openpiar
```

---

## 4. Configurar el backend

### 4.1 Crear entorno virtual e instalar dependencias

```bash
cd /opt/openpiar/backend
python3.13 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt
```

### 4.2 Crear archivo de entorno

```bash
cp .env.example .env
```

Edita `.env` con los valores reales:

```bash
nano .env
```

```bash
APP_ENV=production
SHOW_DOCS=False
CORS_ORIGINS=https://openpiar.mi-colegio.edu.co

SECRET_KEY=<genera con: openssl rand -hex 32>
ACCESS_TOKEN_EXPIRE_MINUTES=480

DB_HOST=localhost
DB_PORT=5432
DB_USER=openpiar_user
DB_PASSWORD=TU_CONTRASENA_SEGURA
DB_NAME=openpiar_db

GEMINI_API_KEY=tu-api-key-de-google-ai-studio
```

**Importante:** no compartas el archivo `.env` ni lo subas a git. Si usas `SHOW_DOCS=True` en produccion, cualquier persona podra ver la documentacion de la API en `/docs`.

### 4.3 Cargar el curriculo nacional

Ejecuta el script que inserta los DBA y EBC en la base de datos:

```bash
.venv/bin/python scripts/seed_curriculum.py
```

Este paso se hace una sola vez. No consume creditos de IA.

### 4.4 Verificar que arranca

Prueba el backend manualmente antes de crear el servicio:

```bash
.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Deberias ver algo como:

```
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8000
```

Detenlo con `Ctrl+C` si funciona.

---

## 5. Crear el servicio de systemd para el backend

Crea el archivo de unidad para que Uvicorn corra como demonio y se reinicie automaticamente:

```bash
sudo nano /etc/systemd/system/openpiar.service
```

Contenido:

```ini
[Unit]
Description=OpenPiar API (Uvicorn)
After=network.target postgresql.service
Requires=postgresql.service

[Service]
User=www-data
Group=www-data
WorkingDirectory=/opt/openpiar/backend
EnvironmentFile=/opt/openpiar/backend/.env
ExecStart=/opt/openpiar/backend/.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 4
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

Explicacion de las opciones:
- `--host 127.0.0.1`: solo acepta conexiones locales. Nginx hara el puente hacia el exterior.
- `--workers 4`: usa 4 procesos worker. Ajusta segun los nucleos de tu VPS (recomendacion: `2 * nucleos + 1`).
- `EnvironmentFile`: carga las variables del `.env` sin exponerlas en la linea de comandos.

Ajusta los permisos del directorio para que `www-data` pueda leerlo:

```bash
sudo chown -R www-data:www-data /opt/openpiar/backend
sudo chmod 600 /opt/openpiar/backend/.env
```

Activa e inicia el servicio:

```bash
sudo systemctl daemon-reload
sudo systemctl enable openpiar
sudo systemctl start openpiar
sudo systemctl status openpiar
```

Para ver los logs en tiempo real:

```bash
sudo journalctl -u openpiar -f
```

---

## 6. Compilar el frontend

```bash
cd /opt/openpiar/frontend
npm install
npm run build
```

Esto genera los archivos estaticos en `frontend/dist/`. Muevelos a la carpeta que servira nginx:

```bash
sudo mkdir -p /var/www/openpiar
sudo cp -r /opt/openpiar/frontend/dist/* /var/www/openpiar/
sudo chown -R www-data:www-data /var/www/openpiar
```

---

## 7. Configurar Nginx

Crea el archivo de sitio:

```bash
sudo nano /etc/nginx/sites-available/openpiar
```

```nginx
server {
    listen 80;
    server_name openpiar.mi-colegio.edu.co;

    # Frontend estatico
    root /var/www/openpiar;
    index index.html;

    # SPA: redirige todas las rutas del frontend a index.html
    location / {
        try_files $uri $uri/ /index.html;
    }

    # API: redirige al backend
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 120s;
    }

    # Headers de seguridad basicos
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
}
```

Habilita el sitio y verifica la configuracion:

```bash
sudo ln -s /etc/nginx/sites-available/openpiar /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default   # Elimina el sitio por defecto
sudo nginx -t                                   # Verifica sintaxis
sudo systemctl reload nginx
```

---

## 8. Configurar HTTPS con Certbot (SSL gratuito)

```bash
sudo certbot --nginx -d openpiar.mi-colegio.edu.co
```

Sigue las instrucciones. Certbot modificara tu config de nginx para anadir SSL y renovara el certificado automaticamente cada 90 dias.

Verifica la renovacion automatica:

```bash
sudo certbot renew --dry-run
```

---

## 9. Configurar el firewall

Si tu VPS usa `ufw`, abre solo los puertos necesarios:

```bash
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw enable
sudo ufw status
```

El puerto 8000 del backend **no** debe abrirse al exterior. Solo Nginx (puertos 80 y 443) recibe trafico publico.

---

## 10. Primer inicio: asistente de configuracion

Abre tu navegador en `https://openpiar.mi-colegio.edu.co`. El sistema detectara que no esta configurado y te mostrara el asistente de configuracion inicial, donde podras:

1. Ingresar los datos de tu institucion (nombre, NIT, codigo DANE, rector, direccion).
2. Subir el PDF del PEI de tu colegio.
3. Crear la cuenta de administrador.

Al terminar, el guardia de configuracion (middleware) se desactivara y la aplicacion quedara lista para usarse.

---

## 11. Mantenimiento y actualizaciones

### Actualizar el codigo

```bash
cd /opt/openpiar
git pull origin main

# Backend
cd backend
.venv/bin/pip install -r requirements.txt
sudo systemctl restart openpiar

# Frontend
cd ../frontend
npm install
npm run build
sudo rm -rf /var/www/openpiar/*
sudo cp -r dist/* /var/www/openpiar/
```

### Aplicar migraciones de base de datos

Si una actualizacion incluye nuevas migraciones de Alembic:

```bash
cd /opt/openpiar/backend
.venv/bin/python -m alembic upgrade head
sudo systemctl restart openpiar
```

### Respaldar la base de datos

Programa un respaldo diario con cron. Crea el script:

```bash
sudo nano /usr/local/bin/backup-openpiar.sh
```

```bash
#!/bin/bash
BACKUP_DIR="/opt/backups/openpiar"
mkdir -p "$BACKUP_DIR"
FILENAME="openpiar_$(date +%Y%m%d_%H%M%S).sql.gz"
sudo -u postgres pg_dump openpiar_db | gzip > "$BACKUP_DIR/$FILENAME"
find "$BACKUP_DIR" -name "*.sql.gz" -mtime +7 -delete
```

```bash
sudo chmod +x /usr/local/bin/backup-openpiar.sh
```

Agrega la entrada de cron (ej: todos los dias a las 2 AM):

```bash
sudo crontab -e
```

```
0 2 * * * /usr/local/bin/backup-openpiar.sh
```

### Monitoreo basico

```bash
# Estado del backend
sudo systemctl status openpiar

# Estado de nginx
sudo systemctl status nginx

# Logs del backend
sudo journalctl -u openpiar -f

# Logs de nginx
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log

# Uso de disco y RAM
df -h
free -h
```

---

## 12. Solucion de problemas comunes

### El backend no arranca

Revisa los logs:

```bash
sudo journalctl -u openpiar -n 50 --no-pager
```

Causas frecuentes:
- PostgreSQL no esta corriendo: `sudo systemctl status postgresql`
- Credenciales incorrectas en `.env`: verifica usuario, contrasena y nombre de la BD.
- El puerto 8000 ya esta en uso: `sudo lsof -i :8000`
- Faltan dependencias de Python: `cd /opt/openpiar/backend && .venv/bin/pip install -r requirements.txt`

### Error 502 Bad Gateway en el navegador

Significa que Nginx no puede comunicarse con Uvicorn. Verifica que el backend este corriendo:

```bash
curl http://127.0.0.1:8000/api/v1/health
```

Si no responde, el backend esta caido. Revisa los logs con `journalctl`.

### Error 412 Precondition Failed

El asistente de configuracion inicial no se ha completado. Ve a la raiz del sitio (`/`) y sigue el wizard de configuracion.

### La IA no funciona

- Verifica que `GEMINI_API_KEY` este configurado en `.env` y que la clave sea valida.
- Asegurate de que el backend se haya reiniciado despues de cambiar `.env`: `sudo systemctl restart openpiar`.

### Permisos denegados al servir archivos estaticos

```bash
sudo chown -R www-data:www-data /var/www/openpiar
sudo chmod -R 755 /var/www/openpiar
```

---

## Resumen de comandos utiles

| Accion | Comando |
|--------|---------|
| Reiniciar backend | `sudo systemctl restart openpiar` |
| Ver logs del backend | `sudo journalctl -u openpiar -f` |
| Reiniciar nginx | `sudo systemctl reload nginx` |
| Recompilar frontend | `cd /opt/openpiar/frontend && npm run build && sudo cp -r dist/* /var/www/openpiar/` |
| Respaldar BD | `sudo -u postgres pg_dump openpiar_db \| gzip > backup.sql.gz` |
| Restaurar BD | `gunzip -c backup.sql.gz \| sudo -u postgres psql openpiar_db` |
| Verificar salud API | `curl http://127.0.0.1:8000/api/v1/health` |
