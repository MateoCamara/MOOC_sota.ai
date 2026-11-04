"""
Módulo 5 · Redacción del estado del arte
========================================
Script: resumir_articulos_ollama.py
Se explica en el vídeo 5.3, "Clasificación de Artículos Completos con Ollama (Demo)".

Qué hace
    1. Lee el Excel clasificado en el Módulo 4.
    2. Filtra los artículos con los criterios de discriminador.txt. Por
       ejemplo, se queda solo con los que respondieron YES a ciertas preguntas.
    3. Para cada artículo que pasa el filtro, lee su PDF (el que descargaste en
       el Módulo 2) y le hace al modelo deepseek-r1:8b las preguntas abiertas
       de clasificador_articulo.txt.
    4. Guarda todo en un Excel nuevo: la columna "Pasa filtro" (YES/NO) y una
       columna por pregunta con las respuestas.

Qué tienes que editar
    - discriminador.txt: un criterio por línea, con el formato Columna=Valor.
      La Columna es el texto exacto de una pregunta de tu clasificador.txt
      del Módulo 4. Por ejemplo:
          Does this paper use deep learning?=YES
      Un artículo pasa el filtro solo si cumple TODOS los criterios.
      Las líneas que empiezan por # son comentarios y se ignoran.
    - clasificador_articulo.txt: tus preguntas abiertas, en inglés, una por
      línea. Por ejemplo: What dataset is used and how many images does it contain?

Entradas
    ../modulo 4/articulos_clasificado_abstract.xlsx   (salida del Módulo 4)
    ../modulo 2/pdfs/<Indice>.pdf                     (PDFs del Módulo 2)
    discriminador.txt y clasificador_articulo.txt

Salidas
    articulos_clasificacion_final.xlsx -> es la entrada del Módulo 8 (Zotero).

Cómo ejecutarlo (desde la carpeta principal del repositorio)
    python "modulo 5/resumir_articulos_ollama.py"

    Es el paso más lento del curso: el modelo lee hasta 15 000 caracteres de
    cada artículo por cada pregunta. Sin una GPU potente, cuenta con varios
    minutos por pregunta.

Requisitos
    - Ollama instalado y en marcha (abre la aplicación o ejecuta "ollama serve").
    - El modelo descargado: ollama pull deepseek-r1:8b
"""

import logging
import os
import re
import sys
from datetime import datetime

import ollama
import pandas as pd
import pypdf


# Si la terminal no puede mostrar algún carácter (por ejemplo, una letra griega
# de un título), se muestra "?" en lugar de detener el programa con un error.
sys.stdout.reconfigure(errors="replace")

# pypdf avisa de pequeños defectos internos de algunos PDFs. No impiden leer el
# texto, así que se ocultan para que no parezcan errores.
logging.getLogger("pypdf").setLevel(logging.ERROR)


# --- 1. Configuración ---

DIRECTORIO_SCRIPT = os.path.dirname(os.path.abspath(__file__))

MODELO = "deepseek-r1:8b"
ARCHIVO_ENTRADA = os.path.join(DIRECTORIO_SCRIPT, "..", "modulo 4", "articulos_clasificado_abstract.xlsx")
DIR_PDFS = os.path.join(DIRECTORIO_SCRIPT, "..", "modulo 2", "pdfs")
ARCHIVO_SALIDA = os.path.join(DIRECTORIO_SCRIPT, "articulos_clasificacion_final.xlsx")
ARCHIVO_DISCRIMINADOR = os.path.join(DIRECTORIO_SCRIPT, "discriminador.txt")
ARCHIVO_CLASIFICADOR = os.path.join(DIRECTORIO_SCRIPT, "clasificador_articulo.txt")

# Cuánto texto de cada artículo se envía al modelo. Las primeras páginas
# (resumen, introducción, método y resultados) suelen bastar, y así cada
# consulta tarda menos.
MAX_PAGINAS = 10
MAX_CARACTERES = 15000

# Ventana de contexto del modelo, en tokens: cuánto texto puede "tener en la
# cabeza" a la vez, contando el prompt y su respuesta. Por defecto Ollama usa
# 4096, y 15 000 caracteres son unos 4 000 tokens: con el valor por defecto no
# queda sitio para que el modelo razone y responda, y acaba perdiendo la
# pregunta. 8192 deja sitio para todo, a cambio de usar algo más de memoria.
NUM_CTX = 8192

# Si el modelo falla varias veces seguidas (por ejemplo, por falta de memoria),
# se detiene el proceso en lugar de llenar el Excel de errores.
MAX_ERRORES_SEGUIDOS = 3

# Nombre de la columna que indica si el artículo ha pasado el filtro.
COLUMNA_FILTRO = "Pasa filtro"


# --- 2. Funciones para hablar con Ollama ---

def comprobar_ollama():
    """Comprueba, antes de empezar, que Ollama está en marcha y tiene el modelo.

    Así el error aparece al principio y no después de un buen rato de proceso.
    """
    try:
        ollama.show(MODELO)
    except ConnectionError:
        print("Error: no se puede conectar con Ollama en http://localhost:11434")
        print("Arranca Ollama (abre la aplicación o ejecuta 'ollama serve') y vuelve a intentarlo.")
        sys.exit(1)
    except ollama.ResponseError as e:
        # El caso más típico es que el modelo no esté descargado.
        print(f"Error de Ollama: {e.error}")
        print(f"Si el modelo no está descargado, ejecuta: ollama pull {MODELO}")
        sys.exit(1)


def limpiar_respuesta(texto):
    """Quita lo que el modelo añade alrededor de la respuesta útil.

    - El razonamiento <think>...</think>: deepseek-r1 es un modelo "razonador"
      y a veces lo incluye antes de la respuesta. Nos quedamos con lo que va
      después del último </think>; si hay un <think> sin cerrar (respuesta
      cortada), se quita desde ahí hasta el final.
    - Las vallas de código (```json, ```markdown...) que rodean la respuesta.
    """
    if "</think>" in texto:
        texto = texto.split("</think>")[-1]
    texto = re.sub(r"<think>.*", "", texto, flags=re.DOTALL)
    texto = re.sub(r"^```\w*\n?", "", texto.strip())
    texto = re.sub(r"\n?```$", "", texto.strip())
    return texto.strip()


def preguntar_ollama(texto_articulo, pregunta):
    """Envía el texto del artículo y una pregunta abierta a Ollama y devuelve la respuesta."""
    # Este es el prompt exacto que recibe el modelo.
    instruccion = (
        f"Based on the following article text, answer the question: '{pregunta}'\n\n"
        f"Article Text:\n{texto_articulo}"
    )

    # Dos intentos: si el primero falla por un error puntual, se reintenta una vez.
    for intento in range(2):
        try:
            respuesta = ollama.chat(
                model=MODELO,
                messages=[{"role": "user", "content": instruccion}],
                options={"num_ctx": NUM_CTX},
            )
            return limpiar_respuesta(respuesta["message"]["content"])
        except ConnectionError:
            raise  # Ollama se ha cerrado: no tiene sentido reintentar (ver main)
        except Exception as e:
            if intento == 0:
                print(f"    Reintentando (error: {e})...")
            else:
                return f"Error Ollama: {str(e)}"


# --- 3. Filtro con el discriminador ---

def leer_lineas(ruta):
    """Devuelve las líneas no vacías de un archivo de texto."""
    # "utf-8-sig" lee bien las tildes y también los archivos guardados como
    # "UTF-8 con BOM" (una opción del Bloc de notas de Windows).
    with open(ruta, "r", encoding="utf-8-sig") as f:
        return [linea.strip() for linea in f if linea.strip()]


def leer_criterios(lineas):
    """Convierte las líneas "Columna=Valor" en una lista de pares (columna, valor)."""
    criterios = []
    for linea in lineas:
        if linea.startswith("#"):
            continue  # Comentario
        if "=" not in linea:
            print(f"  Aviso: se ignora la línea sin '=' en discriminador.txt: {linea}")
            continue
        # rsplit separa por el ÚLTIMO "=", por si la pregunta contiene alguno.
        columna, valor = linea.rsplit("=", 1)
        if not valor.strip():
            print(f"  Aviso: se ignora la línea sin valor después del '=': {linea}")
            continue
        criterios.append((columna.strip(), valor.strip().lower()))
    return criterios


def cumple_criterio(valor_celda, valor_esperado):
    """Comprueba si el contenido de una celda cumple el valor esperado.

    - Si se espera YES o NO, se mira solo la PRIMERA palabra de la respuesta,
      porque el clasificador del Módulo 4 contesta "YES, ..." o "NO. ...".
      Así "YES, it does not use drones" no cuenta como NO por llevar "no"
      dentro, y "**YES**" sí cuenta como YES.
    - Para cualquier otro valor, basta con que la celda lo contenga.
    Ninguna de las dos comprobaciones distingue mayúsculas de minúsculas.
    """
    if pd.isna(valor_celda):
        return False
    texto = str(valor_celda).strip().lower()

    if valor_esperado in ("yes", "no"):
        palabras = re.findall(r"\w+", texto)  # Palabras, sin signos ni asteriscos
        return len(palabras) > 0 and palabras[0] == valor_esperado

    return valor_esperado in texto


def cumple_criterios(fila, criterios):
    """Devuelve True si la fila cumple TODOS los criterios del discriminador."""
    for columna, valor_esperado in criterios:
        if not cumple_criterio(fila[columna], valor_esperado):
            return False
    return True


# --- 4. Lectura de PDFs ---

def extraer_texto_pdf(ruta_pdf):
    """Extrae el texto de las primeras MAX_PAGINAS páginas del PDF.

    Devuelve None si el PDF no se puede leer.
    """
    try:
        lector = pypdf.PdfReader(ruta_pdf)
        texto = ""
        for pagina in lector.pages[:MAX_PAGINAS]:
            # extract_text() puede devolver None en páginas sin texto (imágenes).
            texto += (pagina.extract_text() or "") + "\n"
        return texto
    except Exception as e:
        print(f"    Error leyendo el PDF: {e}")
        return None


# --- 5. Guardar en Excel ---

def guardar_excel(df, ruta):
    """Guarda la tabla en un Excel y devuelve la ruta donde se ha guardado.

    Si el archivo está abierto en Excel, Windows no deja sobrescribirlo
    (PermissionError). En ese caso se guarda una copia con la fecha y la hora
    para no perder el trabajo.
    """
    try:
        df.to_excel(ruta, index=False)
        return ruta
    except PermissionError:
        base, extension = os.path.splitext(ruta)
        ruta_copia = f"{base}_{datetime.now():%Y%m%d-%H%M%S}{extension}"
        df.to_excel(ruta_copia, index=False)
        print(f"\nAviso: no se pudo escribir {os.path.basename(ruta)} (¿lo tienes abierto en Excel?).")
        print(f"Se ha guardado una copia en {os.path.basename(ruta_copia)}.")
        print(f"Cierra Excel y renombra la copia a {os.path.basename(ruta)} para que el siguiente módulo la encuentre.")
        return ruta_copia


# --- 6. Programa principal ---

def main():
    # 6.1. Cargar el Excel del Módulo 4
    print(f"Cargando {os.path.basename(ARCHIVO_ENTRADA)}...")
    try:
        df = pd.read_excel(ARCHIVO_ENTRADA)
    except FileNotFoundError:
        print(f"Error: no se encuentra {ARCHIVO_ENTRADA}")
        print("Asegúrate de ejecutar primero el Módulo 4.")
        sys.exit(1)

    # 6.2. Cargar el discriminador y las preguntas
    try:
        criterios = leer_criterios(leer_lineas(ARCHIVO_DISCRIMINADOR))
    except FileNotFoundError:
        print(f"Error: no se encontró {os.path.basename(ARCHIVO_DISCRIMINADOR)}")
        sys.exit(1)

    try:
        preguntas = leer_lineas(ARCHIVO_CLASIFICADOR)
    except FileNotFoundError:
        print(f"Error: no se encontró {os.path.basename(ARCHIVO_CLASIFICADOR)}")
        sys.exit(1)

    if not preguntas:
        print("Error: clasificador_articulo.txt está vacío. Escribe una pregunta por línea.")
        sys.exit(1)

    print(f"Criterios de filtrado: {criterios}")
    print(f"Preguntas: {len(preguntas)}")
    if not criterios:
        print("Aviso: discriminador.txt no tiene ningún criterio válido: pasan TODOS los artículos.")

    # Cada columna del discriminador tiene que existir en el Excel. Lo más
    # habitual es una pequeña diferencia con el texto de clasificador.txt del
    # Módulo 4 (un espacio, una mayúscula, el signo "?"...).
    columnas_que_faltan = [columna for columna, _ in criterios if columna not in df.columns]
    if columnas_que_faltan:
        print("\nError: estas columnas de discriminador.txt no existen en el Excel:")
        for columna in columnas_que_faltan:
            print(f"  - {columna}")
        print("Columnas disponibles:")
        for columna in df.columns:
            print(f"  - {columna}")
        sys.exit(1)

    # 6.3. Filtrar con el discriminador. La columna "Pasa filtro" queda en el
    # Excel para que el Módulo 8 sepa qué artículos subir a Zotero.
    df[COLUMNA_FILTRO] = ["YES" if cumple_criterios(fila, criterios) else "NO"
                          for _, fila in df.iterrows()]
    seleccionados = df[df[COLUMNA_FILTRO] == "YES"]
    print(f"Artículos que pasan el filtro: {len(seleccionados)} de {len(df)}")

    # Una columna vacía por pregunta; se rellena solo para los seleccionados.
    for pregunta in preguntas:
        df[pregunta] = ""

    if seleccionados.empty:
        # Se guarda igualmente el Excel (todo con "Pasa filtro" = NO) para no
        # dejar el de una ejecución anterior, que confundiría al Módulo 8.
        ruta_guardada = guardar_excel(df, ARCHIVO_SALIDA)
        print("Ningún artículo cumple los criterios. Revisa discriminador.txt.")
        print(f"Se ha guardado {os.path.basename(ruta_guardada)} sin artículos seleccionados.")
        return

    comprobar_ollama()

    # 6.4. Leer el PDF de cada artículo seleccionado y hacerle las preguntas
    procesados = 0
    errores_seguidos = 0
    numero = 0  # Contador para mostrar el progreso [1/N], [2/N]...
    try:
        for i, fila in seleccionados.iterrows():
            numero += 1
            indice_pdf = fila.get("Indice")
            titulo = fila.get("Título")
            if pd.isna(titulo):
                titulo = "Sin título"

            if pd.isna(indice_pdf):
                print(f"\nSaltando fila {i + 1}: no tiene Indice, así que no se sabe cuál es su PDF.")
                continue

            print(f"\n[{numero}/{len(seleccionados)}] [{int(indice_pdf)}] {str(titulo)[:50]}...")

            # Si el Módulo 2 no pudo descargar el PDF, deja "Archivo PDF" vacío.
            if "Archivo PDF" in df.columns and pd.isna(fila.get("Archivo PDF")):
                print("    El Módulo 2 no pudo descargar su PDF. Se salta.")
                continue

            # El Indice relaciona la fila con su PDF: Indice 3 -> pdfs/3.pdf
            ruta_pdf = os.path.join(DIR_PDFS, f"{int(indice_pdf)}.pdf")
            if not os.path.exists(ruta_pdf):
                print(f"    Falta el PDF: {ruta_pdf}")
                print("    (Ejecuta el Módulo 2 para descargar los PDFs.)")
                continue

            texto_pdf = extraer_texto_pdf(ruta_pdf)
            if texto_pdf is None:
                continue
            if not texto_pdf.strip():
                print("    El PDF no tiene texto extraíble (¿es un documento escaneado?). Se salta.")
                continue

            if len(texto_pdf) > MAX_CARACTERES:
                print(f"    Nota: texto truncado de {len(texto_pdf)} a {MAX_CARACTERES} caracteres.")
                texto_pdf = texto_pdf[:MAX_CARACTERES]

            for pregunta in preguntas:
                print(f"    Preguntando: {pregunta}")
                respuesta = preguntar_ollama(texto_pdf, pregunta)
                df.at[i, pregunta] = respuesta
                if respuesta.startswith("Error"):
                    errores_seguidos += 1
                else:
                    errores_seguidos = 0
                if errores_seguidos >= MAX_ERRORES_SEGUIDOS:
                    break

            if errores_seguidos >= MAX_ERRORES_SEGUIDOS:
                print(f"\nError: Ollama ha fallado {errores_seguidos} veces seguidas; se detiene el proceso.")
                print("Si es por falta de memoria, cierra otros programas o baja NUM_CTX/MAX_CARACTERES.")
                break
            procesados += 1

    except ConnectionError:
        print("\nError: se ha perdido la conexión con Ollama. ¿Se ha cerrado?")
        print("Se guarda lo procesado hasta ahora; lo pendiente queda vacío.")
        print("Si vuelves a ejecutar el script, empezará desde el principio.")
    except KeyboardInterrupt:
        print("\nProceso interrumpido (Ctrl+C).")
        print("Se guarda lo procesado hasta ahora; lo pendiente queda vacío.")
        print("Si vuelves a ejecutar el script, empezará desde el principio.")

    # 6.5. Guardar los resultados
    ruta_guardada = guardar_excel(df, ARCHIVO_SALIDA)
    print(f"\nGuardados {len(df)} artículos en {os.path.basename(ruta_guardada)}")
    print(f"({procesados} analizados con su PDF, {len(seleccionados) - procesados} seleccionados "
          f"sin analizar, {len(df) - len(seleccionados)} no pasan el filtro)")


if __name__ == "__main__":
    main()
