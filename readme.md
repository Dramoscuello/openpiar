# OpenPiar: gestor de PIAR comunitario abierto

OpenPiar es una plataforma de código abierto para colegios y docentes de Colombia. Su objetivo es **sistematizar, simplificar y humanizar** la creación, el seguimiento y la transferencia del **Plan Individual de Ajustes Razonables (PIAR)** de los estudiantes con discapacidad o con Trastornos Específicos del Aprendizaje (TEAp), junto con su historia escolar.

La plataforma transforma la gestión documental del PIAR en un proceso guiado, acompañado por un asistente pedagógico de inteligencia artificial, y produce los documentos oficiales exigidos por la normativa colombiana.

---

## Marco normativo y pedagógico

El diseño de OpenPiar sigue los lineamientos del Ministerio de Educación Nacional (MEN) y el marco legal colombiano:

- **Decreto 1421 de 2017:** regula la atención educativa a personas con discapacidad y establece el PIAR como herramienta obligatoria para planear los apoyos escolares.
- **Ley 2216 de 2022:** promueve la educación inclusiva para estudiantes con Trastornos Específicos del Aprendizaje (dislexia, TDAH, discalculia, entre otros), garantizando sus ajustes curriculares.
- **Decreto 1860 de 1994:** garantiza que las planeaciones y los manuales de convivencia respeten la autonomía y la identidad del PEI de cada institución.
- **Diseño Universal para el Aprendizaje (DUA):** base pedagógica del sistema. Flexibiliza la enseñanza mediante múltiples formas de representación (el qué), de acción y expresión (el cómo) y de implicación (el porqué).

---

## Funcionalidades

### Asistente de configuración inicial
La primera vez que se abre la plataforma, un asistente solicita los datos de la institución (nombre, NIT, código DANE, rector, dirección), la API key de Gemini (opcional, se guarda en la base de datos), el PEI en PDF para que la IA extraiga el modelo pedagógico y los valores institucionales, y crea la cuenta de administrador. La configuración queda bloqueada hasta completar este paso.

### Gestión escolar
Módulo administrativo para registrar sedes, docentes, directivos, áreas, asignaturas, grados, grupos y carga académica. Incluye la gestión de **periodos académicos** con año lectivo, fechas y un único periodo activo a la vez; al activar un periodo se prepara automáticamente la cobertura de asignaturas de los PIAR correspondientes.

### Registro y valoración del estudiante (Anexo 1)
Formulario guiado con la información general, el entorno de salud, el entorno de hogar, la trayectoria educativa y la matrícula actual. Admite el soporte médico en PDF y guarda borradores locales.

### Gestión del PIAR por periodos (Anexo 2)
- **Matriz de ajustes razonables por área y periodo**, con objetivos, barreras, tipo de ajuste, apoyos, estrategias, temporalidad, responsable y medios de verificación.
- **Asistencia con IA:** el asistente usa el perfil del estudiante, el PEI de la institución, el área, el tema y las barreras definidas por el docente para proponer ajustes DUA. La propuesta siempre es editable.
- **Cobertura de asignaturas:** cada asignatura de la carga académica se resuelve como "con ajuste" o "sin ajuste" (con justificación).
- **Evidencias:** se adjuntan imágenes de la implementación de los ajustes y se incluyen en el PDF oficial.
- **Historial de cambios:** registro de auditoría de cada modificación, con exportación a PDF.
- **Finalización y versionado:** al finalizar un periodo se genera una versión inmutable del PDF oficial con su huella SHA-256. El periodo puede reabrirse para crear una versión nueva conservando las anteriores.

### Acta de acuerdo y corresponsabilidad familiar (Anexo 3)
Compromisos del establecimiento (aula) y de la familia (casa), fecha de firma y firmas de los actores. Se genera el acta oficial en PDF.

### Panel de familia
Acceso público mediante un código por estudiante, sin autenticación. La familia consulta los ajustes y compromisos del periodo activo, registra su firma y descarga el acta en PDF.

### Directorio de acudientes y panel institucional
Directorio de contactos de acudientes para la gestión institucional y un panel con estadísticas agregadas (estudiantes, PIAR, ajustes, periodos y actividad reciente).

### Historia escolar portable
Exportación e importación del expediente en un archivo cifrado `.openpiar` (AES-256-GCM con PBKDF2-HMAC-SHA256), útil cuando un estudiante cambia de institución.

### Roles y permisos
- **Directivo:** administración general, configuración institucional y gestión escolar.
- **Docente de aula, docente de apoyo y orientador:** diligenciamiento del PIAR según su asignación.
- **Director de grupo:** gestiona el PIAR de los estudiantes de su grupo, independientemente de su rol.

### Tour de bienvenida
En el primer inicio de sesión, una guía interactiva presenta la navegación general, la gestión de estudiantes y la creación del PIAR.

---

## Guía de uso

1. **Configurar la institución.** Completa el asistente inicial con los datos del colegio, la clave de Gemini (opcional), el PEI y la cuenta de administrador.
2. **Preparar la gestión escolar.** Registra sedes, grados, grupos, asignaturas, carga académica y crea el periodo académico activo.
3. **Registrar estudiantes.** Ingresa la valoración del Anexo 1 y el soporte médico cuando aplique.
4. **Crear el PIAR del periodo.** Define los ajustes por asignatura; puedes apoyarte en la IA y editar libremente la propuesta.
5. **Adjuntar evidencias.** Sube imágenes de la implementación de los ajustes.
6. **Diligenciar el acta.** Registra los compromisos de aula y de casa, la fecha de firma y los firmantes.
7. **Finalizar el periodo.** Genera la versión inmutable, descarga el PDF oficial y comparte el código de acceso con la familia.
8. **Transferir el expediente.** Exporta el archivo `.openpiar` si el estudiante cambia de institución.

---

## Instalación

### Docker Compose (recomendado)
Consulta [deploy-docker.md](deploy-docker.md). Solo requiere Docker y un archivo `.env` en la raíz con las credenciales de PostgreSQL y la clave de firma JWT.

### Instalación tradicional en VPS
Consulta [deploy.md](deploy.md) para el despliegue con Nginx, Uvicorn y PostgreSQL.

### Desarrollo local
Backend (workdir `backend/`):

```bash
python3.13 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env
.venv/bin/python scripts/init_db.py
.venv/bin/python -m uvicorn app.main:app --reload --port 8000
```

Frontend (workdir `frontend/`):

```bash
npm install
npm run dev
```

Pruebas:

```bash
# Backend
.venv/bin/python -m pytest tests/ -v

# Frontend
npm test
npm run type-check
```

---

## Configuración de la IA

OpenPiar usa Google Gemini para el análisis del PEI y la generación de ajustes. La clave se resuelve con prioridad **base de datos, luego variable de entorno**:

1. Se puede ingresar durante el asistente de configuración inicial o, después, como directivo, en **Gestión Escolar, Configuración**.
2. `GEMINI_API_KEY` en el archivo `.env` funciona como respaldo para desarrollo.

---

## Licencia y contribución

OpenPiar se distribuye bajo la licencia **GNU General Public License v3.0 (GPL-3.0)**.

- [CONTRIBUTING.md](CONTRIBUTING.md): guía de contribución.
- [SECURITY.md](SECURITY.md): política de seguridad.
- [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md): código de conducta.
