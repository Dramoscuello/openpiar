# 🇨🇴 OpenPiar: Gestor de PIAR Comunitario Abierto

¡Bienvenido a **OpenPiar**! Una plataforma de código abierto (*open-source*) diseñada específicamente para los colegios y docentes de Colombia. 

El objetivo de esta herramienta es **sistematizar, simplificar y humanizar** la creación, seguimiento y transferencia del **Plan Individual de Ajustes Razonables (PIAR)** y la **Historia Escolar** de los estudiantes con discapacidad o Trastornos Específicos del Aprendizaje (TEAp).

---

## 📌 ¿De qué trata el proyecto?

Crear un PIAR suele convertirse en una tarea administrativa abrumadora que consume valioso tiempo que los docentes prefieren pasar enseñando. **OpenPiar** transforma este papeleo en un proceso interactivo acompañado por un **Asistente Pedagógico de Inteligencia Artificial**. 

Al ser una aplicación comunitaria:
1.  **Se adapta a tu colegio:** Al iniciar la plataforma, puedes cargar el **PEI (Proyecto Educativo Institucional)** de tu colegio para que las sugerencias de la IA sigan el modelo pedagógico y la identidad de tu institución.
2.  **Es gratuito y colaborativo:** Sin costos de licencias privadas. Además, cuenta con un banco de estrategias donde los docentes de todo el país pueden compartir (de forma anónima) las adaptaciones que mejor funcionan en sus aulas.

---

## 📚 ¿En qué normas y pedagogías se basa?

El diseño de OpenPiar cumple rigurosamente con los lineamientos del Ministerio de Educación Nacional (MEN) y el marco legal colombiano:

*   **Decreto 1421 de 2017:** Regula la atención educativa a personas con discapacidad y establece el PIAR como la herramienta obligatoria para planear los apoyos escolares y el Plan de Mejoramiento Institucional (PMI).
*   **Ley 2216 de 2022:** Promueve la educación inclusiva para estudiantes con Trastornos Específicos del Aprendizaje (TEAp) como la dislexia, el TDAH o la discalculia, garantizando sus ajustes curriculares sin necesidad de certificados clínicos de discapacidad.
*   **Decreto 1860 de 1994:** Garantiza que las planeaciones y manuales de convivencia respeten la autonomía y la identidad del PEI de cada institución.
*   **Diseño Universal para el Aprendizaje (DUA):** La base pedagógica del sistema. Busca flexibilizar las clases para que todos aprendan mediante múltiples formas de:
    *   **Representación (El qué):** Cómo se presenta la información.
    *   **Acción y Expresión (El cómo):** Cómo los estudiantes demuestran lo aprendido.
    *   **Implicación (El porqué):** Cómo se motiva y compromete a los estudiantes.

---

## ⚙️ ¿Cómo funciona? (Nuestros Módulos)

### 0️⃣ Asistente de Configuración e Identidad (Instalador)
La primera vez que abres OpenPiar, un asistente te pedirá:
*   Datos básicos de tu colegio (Nombre, NIT, Código DANE, rector, dirección).
*   Subir el archivo PDF del **PEI** de tu institución. La IA lo analizará para aprender tu modelo educativo (ej: constructivista, tradicional, etc.) y personalizar todas las planeaciones futuras.

### 1️⃣ Valoración Pedagógica del Estudiante (Anexo 1)
Un formulario amigable paso a paso para recopilar la mirada integral del estudiante:
*   **Entornos de salud y hogar:** Terapias, diagnósticos, apoyos requeridos (silla de ruedas, audífonos, etc.) y dinámica familiar.
*   **Dimensiones del desarrollo:** Fortalezas y necesidades cognitivas, comunicativas, socioafectivas y corporales.

### 2️⃣ Generador Inteligente de Ajustes (Anexo 2)
*   **Búsqueda del Currículo:** Selecciona el grado y área (Matemáticas, Lenguaje, Ciencias, etc.). El sistema tiene cargados en su base de datos los **Derechos Básicos de Aprendizaje (DBA)** y **Estándares Básicos de Competencias (EBC)** oficiales del país.
*   **Asistencia con IA DUA:** El asistente de IA toma el perfil del estudiante (Anexo 1) y el DBA seleccionado para generar una propuesta de ajustes didácticos y evaluativos basados en la Taxonomía de Bloom (por ejemplo, sugiriendo simplificar el nivel del verbo de una meta si el estudiante tiene dificultades cognitivas).
*   **Human-in-the-loop:** La IA propone, pero tú decides. Puedes editar, borrar o complementar cualquier sugerencia para adaptarla a los recursos de tu salón de clases.

### 3️⃣ Banco de Estrategias Comunitarias
Cuando un maestro modifica una sugerencia de la IA para adaptarla a su realidad, esa estrategia "validada en el aula" alimenta de forma anónima una base de conocimientos. La IA aprenderá de las soluciones reales de otros maestros en Colombia.

### 4️⃣ Acta de Corresponsabilidad Familiar (Anexo 3)
Genera de forma automática el documento oficial en formato PDF. Incluye una tabla interactiva para planificar las actividades y compromisos semanales que la familia realizará en casa durante los recesos escolares.

### 5️⃣ Historia Escolar Portable
Si un estudiante es trasladado de colegio o promovido de grado, puedes exportar su expediente en un archivo seguro y encriptado (`.openpiar`). El nuevo colegio solo tendrá que importar el archivo para continuar con sus apoyos sin empezar de cero.

---

## 🚀 Guía de Uso Paso a Paso (Para Docentes)

### Paso 1: Configurar el Colegio
Al abrir la aplicación por primera vez, rellena los datos de tu institución, sube tu documento del PEI y crea el usuario del administrador de la escuela.

### Paso 2: Seguir el Tour de Bienvenida
En tu primer inicio de sesión, una guía interactiva en pantalla te mostrará la ubicación del menú de estudiantes, la base de datos de DBA y el generador de PIAR.

### Paso 3: Registrar al Estudiante (Anexo 1)
Ve a **"Estudiantes"**, presiona **"Nuevo Estudiante"** y rellena el formulario de valoración pedagógica. El sistema guardará borradores automáticos a medida que escribes por si pierdes la conexión.

### Paso 4: Diseñar los Ajustes (Anexo 2)
Entra al perfil del estudiante, selecciona **"Crear PIAR"**, elige la materia y el objetivo de aprendizaje (DBA). Haz clic en **"Generar con IA"**. Revisa las sugerencias de DUA adaptadas a tu PEI y edítalas según los materiales de tu aula.

### Paso 5: Firmar el Acta (Anexo 3)
Añade las actividades de apoyo en casa para la familia, genera el PDF institucional y descárgalo para la firma física o digital del directivo, docentes y acudientes.

---

## ⚡ Carga del Currículo Nacional (DBA y EBC)

El proyecto viene con los listados de Derechos Básicos de Aprendizaje y Estándares precargados en archivos locales para consulta inmediata.

Si estás instalando la aplicación, debes pasar estos datos a la base de datos del programa. Para hacerlo, abre una terminal y ejecuta el siguiente comando:

```bash
cd backend
.venv/bin/python scripts/seed_curriculum.py
```

> [!NOTE]
> Este paso **no consume créditos ni tokens** de Inteligencia Artificial. Una vez ejecutado, el buscador de asignaturas y competencias estará disponible inmediatamente para todos los docentes.

