# SOTA.ai · Código del curso

Scripts en Python del MOOC **[SOTA.ai. Inteligencia Artificial para estar al día del mundo científico](https://moodle.upm.es/en-abierto/course/view.php?id=293)** (UPM En Abierto, ETSIT-UPM).

Con estos scripts automatizas el flujo de trabajo de un estado del arte con IA generativa **local**:

1. Buscas y descargas artículos de arXiv.
2. Los clasificas con un modelo de lenguaje que se ejecuta en tu ordenador (Ollama + `deepseek-r1:8b`).
3. Extraes información de los PDFs.
4. Llevas el resultado a tu gestor bibliográfico (Zotero).

Cada script se explica en un vídeo de demostración y en la Guía Práctica de su módulo en Moodle.

---

## Índice

- [Qué hay en este repositorio](#qué-hay-en-este-repositorio)
- [El pipeline de un vistazo](#el-pipeline-de-un-vistazo)
- [Requisitos](#requisitos)
- [Instalación paso a paso](#instalación-paso-a-paso)
- [Cómo adaptarlo a tu tema](#cómo-adaptarlo-a-tu-tema)
- [Módulo a módulo](#módulo-a-módulo)
- [Archivos de ejemplo incluidos](#archivos-de-ejemplo-incluidos)
- [Problemas frecuentes](#problemas-frecuentes)
- [Buenas prácticas](#buenas-prácticas)
- [Licencia y dudas](#licencia-y-dudas)

---

## Qué hay en este repositorio

| Módulo del curso | Carpeta | Qué contiene |
|---|---|---|
| 1 · Introducción al SOTA y la IA | `modulo 1/` | `url.txt`: ejemplo de búsqueda avanzada en arXiv con operadores booleanos. No hay que ejecutar nada. |
| 2 · Búsqueda y evaluación de fuentes | `modulo 2/` | `descargar_articulos_arxiv.py`: busca en arXiv y descarga artículos y PDFs. |
| 3 · Ollama y modelos locales | `modulo 3/` | `run_prompts.py` y `validate_outputs.py`: plantillas de prompting con salida verificable. |
| 4 · Extracción estructurada y análisis | `modulo 4/` | `resumir_abstracts_ollama.py`: clasifica los abstracts con preguntas YES/NO. |
| 5 · Redacción del estado del arte | `modulo 5/` | `resumir_articulos_ollama.py`: filtra artículos y los analiza leyendo sus PDFs. |
| 8 · Gestión bibliográfica y Zotero | `modulo 8/` | `exportar_zotero.py`: sube los artículos seleccionados a tu biblioteca de Zotero. |

Los módulos 6, 7, 9, 10 y 11 no necesitan código: se trabajan con las guías, las plantillas de prompting y los cuestionarios de Moodle.

## El pipeline de un vistazo

Los módulos 2, 4, 5 y 8 forman una cadena: **la salida de cada uno es la entrada del siguiente**. El módulo 3 es independiente y sirve para practicar con Ollama.

```text
M2  query.txt ─────────────► descargar_articulos_arxiv.py ─► articulos.xlsx + pdfs/
                                                                  │
M4  clasificador.txt ──────► resumir_abstracts_ollama.py ◄────────┘
                                   │
                                   ▼
                     articulos_clasificado_abstract.xlsx
                                   │
M5  discriminador.txt ─────► resumir_articulos_ollama.py ◄── pdfs/ (del M2)
    clasificador_articulo.txt      │
                                   ▼
                     articulos_clasificacion_final.xlsx
                                   │
M8  zotero_config.txt ─────► exportar_zotero.py ─► tu biblioteca de Zotero

M3  (aparte)  plantillas .txt ─► run_prompts.py ─► outputs/ ─► validate_outputs.py
```

## Requisitos

- **Python 3.11 o superior** ([python.org](https://www.python.org/downloads/)). Si ya lo tienes, compruébalo con `python --version`.
- **Ollama** ([ollama.com](https://ollama.com/download)) con el modelo `deepseek-r1:8b`, para los módulos 3, 4 y 5. El modelo ocupa unos 5,2 GB y necesita unos 6 GB de RAM libre, y unos 7 GB en el Módulo 5, que trabaja con textos más largos. Con una tarjeta gráfica (GPU) va mucho más rápido, pero no es imprescindible.
- **Conexión a Internet** para los módulos 2 (arXiv) y 8 (Zotero).
- **Una cuenta de Zotero** ([zotero.org](https://www.zotero.org/user/register)) para el módulo 8.

## Instalación paso a paso

**1. Descarga el código.** Pulsa el botón verde **Code → Download ZIP** de esta página y descomprímelo. Si usas git, también puedes hacer `git clone`.

**2. Abre una terminal en la carpeta del repositorio**, la que contiene este README. En Windows, abre la carpeta en el Explorador y luego:
- haz clic derecho en un hueco vacío y elige *Abrir en Terminal*;
- o escribe `cmd` en la barra de direcciones y pulsa Intro.

**3. Crea y activa un entorno virtual.** Es una instalación de Python solo para este curso, que no interfiere con nada más.

Windows:

```text
python -m venv .venv
.venv\Scripts\activate
```

macOS / Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

En Debian o Ubuntu, si `venv` da error, instálalo antes con `sudo apt install python3-venv`.

Sabrás que el entorno está activo porque verás `(.venv)` al principio de la línea de la terminal. **Actívalo cada vez que abras una terminal nueva** para trabajar en el curso.

**4. Instala las librerías:**

```bash
pip install -r requirements.txt
```

**5. Instala Ollama y descarga el modelo.** Instala Ollama desde [ollama.com](https://ollama.com/download) y, con Ollama abierto, ejecuta:

```bash
ollama pull deepseek-r1:8b
ollama list
```

`ollama list` debe mostrar `deepseek-r1:8b`. La Guía Operativa del Módulo 3 explica la instalación en detalle.

## Cómo adaptarlo a tu tema

En el curso trabajas un **Proyecto Acumulativo**: el tema que eliges en el Módulo 1 se reutiliza en todos los módulos. Cada carpeta trae un ejemplo, y en algunos módulos el ejemplo es distinto: detección de enfermedades en plantas en los módulos 2, 4 y 5, y técnicas de estudio en el 3. **Sustitúyelos por los de tu tema.** Solo tienes que editar estos archivos de texto:

| Módulo | Archivo | Qué escribir |
|---|---|---|
| 2 | `modulo 2/query.txt` | Tu cadena de búsqueda para arXiv. |
| 3 | `modulo 3/run_prompts.py` (variables `TEMA`, `IDIOMA`, `AUDIENCIA`) | Tu tema, idioma y audiencia. |
| 4 | `modulo 4/clasificador.txt` | 3 preguntas YES/NO en inglés, una por línea. |
| 5 | `modulo 5/discriminador.txt` | Criterios `Columna=Valor` para filtrar. |
| 5 | `modulo 5/clasificador_articulo.txt` | Preguntas abiertas en inglés sobre el artículo completo. |
| 8 | `modulo 8/zotero_config.txt` | Tus datos de Zotero (biblioteca y API key). |

Guarda siempre los `.txt` con codificación **UTF-8**, que es la opción por defecto en casi todos los editores.

## Módulo a módulo

Todos los comandos se ejecutan **desde la carpeta principal del repositorio**, con el entorno virtual activado. Las comillas son necesarias porque los nombres de las carpetas llevan espacio.

### Módulo 1 · Introducción al SOTA y la IA

`modulo 1/url.txt` contiene una URL de ejemplo de la búsqueda avanzada de arXiv: combina varios términos con AND/OR y ordena los resultados por fecha. Ábrela en el navegador para ver cómo se traduce una pregunta de investigación en una búsqueda. No hay que ejecutar nada.

### Módulo 2 · Búsqueda y descarga de artículos de arXiv

```bash
python "modulo 2/descargar_articulos_arxiv.py"
```

- **Editas:** `query.txt` con tu cadena de búsqueda. arXiv admite `AND`, `OR`, `ANDNOT`, comillas y paréntesis, por ejemplo `("plant disease" OR "leaf disease") AND detection`. Dentro del script, `MAX_RESULTADOS` fija cuántos artículos se descargan (20 por defecto).
- **Obtienes:**
  - `articulos.xlsx`: una fila por artículo con `Indice`, `Título`, `Autores`, `Fecha`, `Año`, `Abstract`, `DOI`, `URL` y `Archivo PDF`.
  - La carpeta `pdfs/` con `1.pdf`, `2.pdf`, etc. El número es el `Indice` del Excel.
- **Tiempo:** 1–2 minutos, porque el script espera unos segundos entre descargas para no saturar arXiv.
- **Vídeo:** 2.4, "Descarga de Artículos desde arXiv".

### Módulo 3 · Plantillas de prompting con salida verificable

```bash
python "modulo 3/run_prompts.py"
python "modulo 3/validate_outputs.py"
```

- **Editas:** las variables `TEMA`, `IDIOMA` y `AUDIENCIA` al principio de `run_prompts.py`. Si quieres, también las plantillas `plantilla_*.txt`: los huecos `{TEMA}`, `{IDIOMA}` y `{AUDIENCIA}` se rellenan solos.
- **Obtienes:**
  - En `outputs/`: `tabla_keywords.md` (tabla Markdown), `ficha_tema.json` y `plan_sota.json`.
  - Tras la validación, `outputs/verificacion.md` con un PASS o FAIL por archivo.
- **Cómo funciona:** el script habla con Ollama a través de su **API REST nativa** (`http://localhost:11434/api/chat`), con `temperature=0` para obtener respuestas lo más deterministas posible.
- **Tiempo:** de 1 a 10 minutos según tu ordenador.
- **Vídeo:** 3.3, "Plantillas de Prompting con Salida Verificable".

### Módulo 4 · Clasificación de abstracts con Ollama

```bash
python "modulo 4/resumir_abstracts_ollama.py"
```

- **Editas:** `clasificador.txt`, con una pregunta YES/NO en inglés por línea, alineada con tu tema.
- **Lee:** `modulo 2/articulos.xlsx`.
- **Obtienes:** `articulos_clasificado_abstract.xlsx`, el Excel del Módulo 2 con **una columna nueva por pregunta**. El nombre de cada columna es el texto exacto de la pregunta.
- **Cómo funciona:**
  - Envía cada abstract y cada pregunta al modelo y le pide que empiece su respuesta por YES o NO.
  - Si una consulta falla, la reintenta una vez.
  - Elimina el razonamiento `<think>…</think>` que a veces añade el modelo.
- **Tiempo:** el modelo responde a cada pregunta de cada artículo, así que con 20 artículos y 3 preguntas hace 60 consultas. Puede tardar de 10 minutos a más de una hora.
- **Vídeo:** 4.3, "Clasificación de Abstracts con Ollama".

### Módulo 5 · Análisis de los artículos completos

```bash
python "modulo 5/resumir_articulos_ollama.py"
```

- **Editas:**
  - `discriminador.txt`: un criterio por línea con el formato `Columna=Valor`. La columna es una pregunta de `modulo 4/clasificador.txt` y tiene que ser **idéntica** a ella. Por ejemplo, `Does this paper use deep learning?=YES`. Un artículo pasa el filtro solo si cumple **todos** los criterios. Las líneas que empiezan por `#` son comentarios.
    - Con `YES` o `NO` se mira la primera palabra de la respuesta del Módulo 4.
    - Con cualquier otro valor basta con que la celda lo contenga.
  - `clasificador_articulo.txt`: preguntas abiertas en inglés, una por línea.
- **Lee:** `modulo 4/articulos_clasificado_abstract.xlsx` y los PDFs de `modulo 2/pdfs/`.
- **Obtienes:** `articulos_clasificacion_final.xlsx` con:
  - la columna **`Pasa filtro`** (YES/NO), que usa el Módulo 8;
  - una columna por pregunta, con la respuesta para cada artículo que pasa el filtro.
- **Cómo funciona:** lee las **10 primeras páginas** de cada PDF y envía como máximo **15 000 caracteres** al modelo. Para que todo ese texto quepa, amplía la ventana de contexto del modelo a 8192 tokens (`NUM_CTX`).
- **Tiempo:** es el paso más lento del curso. En un portátil con una GPU de 6 GB, cada pregunta sobre un artículo tarda entre 5 y 10 minutos.
- **Vídeo:** 5.3, "Clasificación de Artículos Completos con Ollama".

### Módulo 8 · Exportación a Zotero

```bash
python "modulo 8/exportar_zotero.py"
```

- **Editas:** `zotero_config.txt`, que explica dentro cómo conseguir cada dato:
  - `library_id` y `api_key`, en [zotero.org/settings/keys](https://www.zotero.org/settings/keys). La clave necesita **permiso de escritura**.
  - `library_type`.
  - Opcionalmente, la `collection_key` de la colección donde quieres los artículos.
- **Lee:** `modulo 5/articulos_clasificacion_final.xlsx` y `modulo 5/clasificador_articulo.txt`.
- **Obtienes:** en tu biblioteca de Zotero, un ítem de tipo *Preprint* por cada artículo con `Pasa filtro = YES`. Cada ítem lleva:
  - título, autores, fecha, abstract, URL, DOI e identificador de arXiv;
  - una **nota** con las respuestas del Módulo 5;
  - la etiqueta `sota-ai`.
- **Ejecuciones repetidas:** si lo ejecutas dos veces, no duplica lo que ya subió.
- **Para probar sin tocar tu biblioteca:** pon `SIMULAR = True` dentro del script.
- **Vídeo:** 8.3, "Del Pipeline a Zotero".

## Archivos de ejemplo incluidos

El repositorio incluye las salidas de ejecutar los scripts con los temas de ejemplo: `modulo 2/articulos.xlsx`, `modulo 4/articulos_clasificado_abstract.xlsx` y la carpeta `modulo 3/outputs/`. Así puedes ver qué produce cada paso antes de ejecutarlo. **Cuando ejecutes los scripts, esos archivos se sobrescribirán con los resultados de tu tema.**

No se incluyen:
- **Los PDFs**, porque los derechos son de sus autores. Se descargan al ejecutar el Módulo 2.
- **El Excel del Módulo 5** (`articulos_clasificacion_final.xlsx`), porque necesita esos PDFs. Se crea al ejecutar el Módulo 5.

## Problemas frecuentes

| Problema | Solución |
|---|---|
| `no se puede conectar con Ollama en http://localhost:11434` | Ollama no está en marcha. Abre la aplicación de Ollama o ejecuta `ollama serve` en otra terminal. |
| `model 'deepseek-r1:8b' not found` | Falta descargar el modelo: `ollama pull deepseek-r1:8b`. |
| `Ollama ha fallado 3 veces seguidas` | Suele ser falta de memoria. Cierra otros programas y vuelve a ejecutar el script. |
| `validate_outputs.py` da `FAIL: ... no es un JSON válido` | El modelo no ha respetado el formato, por ejemplo cerrando una lista con `}` en vez de `]`. Detectarlo es justo el trabajo del validador. Vuelve a ejecutar `run_prompts.py` o refuerza las instrucciones de la plantilla. |
| `ModuleNotFoundError: No module named ...` | El entorno virtual no está activado o faltan librerías. Activa `.venv` (paso 3) y ejecuta `pip install -r requirements.txt`. |
| `"python" no se reconoce como un comando` | Python no está instalado o no está en el PATH. En Windows prueba con `py` en lugar de `python`. Si usas el instalador clásico de python.org, reinstala marcando *Add python.exe to PATH*. |
| PowerShell no deja ejecutar `.venv\Scripts\activate` | Usa el *Símbolo del sistema* (cmd), donde funciona sin cambios, o permite los scripts locales con `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`. |
| `Aviso: no se pudo escribir ... (¿lo tienes abierto en Excel?)` | Tenías el Excel de salida abierto. El script ha guardado una copia con la fecha. Cierra Excel y renombra la copia al nombre original para que el siguiente módulo la encuentre. |
| `estas columnas de discriminador.txt no existen en el Excel` | El texto de la pregunta en `discriminador.txt` debe ser **idéntico** al de `clasificador.txt` del Módulo 4: mismas mayúsculas, espacios y signo `?`. Lo más seguro es copiarlo y pegarlo. |
| `Falta el PDF: ...` en el Módulo 5 | Ejecuta antes el Módulo 2 para descargar los PDFs. |
| Los modelos van muy lentos | Sin GPU es normal. Empieza con pocos artículos (`MAX_RESULTADOS` en el M2) y pocas preguntas, y cierra otros programas pesados. |
| arXiv devuelve 0 resultados o da error | Simplifica la búsqueda (menos términos, más sinónimos con `OR`). Si arXiv te limita por hacer muchas peticiones, espera unos minutos. |
| Zotero: `la API key no tiene permiso de escritura` | Edita la clave en [zotero.org/settings/keys](https://www.zotero.org/settings/keys) y marca *Allow write access*. |
| Tildes o eñes que se ven mal | Guarda los `.txt` con codificación UTF-8. |

## Buenas prácticas

- **Privacidad:** Ollama ejecuta el modelo en tu ordenador, así que los textos que analizas no salen de tu máquina.
- **Tu API key de Zotero es personal**, como una contraseña. No la compartas, no la subas a GitHub y no la incluyas en tus entregas.
- **Respeta las condiciones de arXiv:** el script espera entre descargas. No elimines esa pausa ni descargues miles de artículos de golpe.
- **La IA se equivoca.** Verifica las respuestas del modelo contra el artículo original (método claims→evidence del Módulo 6) y declara el uso de IA en tus trabajos (Módulo 7).

## Licencia y dudas

El código se distribuye con licencia [MIT](LICENSE).

Las dudas sobre cada script se resuelven en el **foro de dudas de su módulo** en Moodle. Si sabes la respuesta a la duda de un compañero, ¡contesta!
