"""
Módulo 4 · Extracción estructurada y análisis
=============================================
Script: resumir_abstracts_ollama.py
Se explica en el vídeo 4.3, "Clasificación de Abstracts con Ollama (Demo)".

Qué hace
    Lee los artículos que descargaste en el Módulo 2 (articulos.xlsx) y, para
    cada abstract, le hace al modelo local deepseek-r1:8b las preguntas
    YES/NO de clasificador.txt. Guarda las respuestas en un Excel nuevo con
    una columna por pregunta.

Qué tienes que editar
    - clasificador.txt: escribe tus preguntas YES/NO, en inglés, una por
      línea y alineadas con tu tema. Por ejemplo:
          Does this paper use deep learning?
      El texto de cada pregunta será el nombre de su columna en el Excel. El
      discriminador.txt del Módulo 5 usará esos mismos nombres.

Entradas
    ../modulo 2/articulos.xlsx   (salida del Módulo 2)
    clasificador.txt

Salidas
    articulos_clasificado_abstract.xlsx -> el Excel del Módulo 2 más una
    columna por pregunta. Es la entrada del Módulo 5.

Cómo ejecutarlo (desde la carpeta principal del repositorio)
    python "modulo 4/resumir_abstracts_ollama.py"

    Tarda bastante: el modelo responde a cada pregunta de cada artículo. Con 20
    artículos y 3 preguntas hace 60 consultas, que pueden llevar de 10 minutos
    a más de una hora según tu ordenador.

Requisitos
    - Ollama instalado y en marcha (abre la aplicación o ejecuta "ollama serve").
    - El modelo descargado: ollama pull deepseek-r1:8b
"""

import os
import re
import sys
from datetime import datetime

import ollama
import pandas as pd


# Si la terminal no puede mostrar algún carácter (por ejemplo, una letra griega
# de un título), se muestra "?" en lugar de detener el programa con un error.
sys.stdout.reconfigure(errors="replace")


# --- 1. Configuración ---

DIRECTORIO_SCRIPT = os.path.dirname(os.path.abspath(__file__))

MODELO = "deepseek-r1:8b"
ARCHIVO_ENTRADA = os.path.join(DIRECTORIO_SCRIPT, "..", "modulo 2", "articulos.xlsx")
ARCHIVO_SALIDA = os.path.join(DIRECTORIO_SCRIPT, "articulos_clasificado_abstract.xlsx")
ARCHIVO_CLASIFICADOR = os.path.join(DIRECTORIO_SCRIPT, "clasificador.txt")

# Si el modelo falla varias veces seguidas (por ejemplo, por falta de memoria),
# se detiene el proceso en lugar de llenar el Excel de errores.
MAX_ERRORES_SEGUIDOS = 3


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


def pedir_a_ollama(abstract, pregunta):
    """Envía el abstract y una pregunta YES/NO a Ollama y devuelve la respuesta."""
    # Este es el prompt exacto que recibe el modelo. Se escribe en inglés
    # porque los abstracts de arXiv están en inglés.
    instruccion = (
        f"Based on the following academic abstract, answer the question: '{pregunta}'\n"
        f"Answer with only 'YES' or 'NO', optionally followed by a very short explanation.\n\n"
        f"Abstract:\n{abstract}"
    )

    # Dos intentos: si el primero falla por un error puntual, se reintenta una vez.
    for intento in range(2):
        try:
            respuesta = ollama.chat(model=MODELO, messages=[
                {"role": "user", "content": instruccion},
            ])
            return limpiar_respuesta(respuesta["message"]["content"])
        except ConnectionError:
            raise  # Ollama se ha cerrado: no tiene sentido reintentar (ver main)
        except Exception as e:
            if intento == 0:
                print(f"    Reintentando (error: {e})...")
            else:
                return f"Error: {str(e)}"


# --- 3. Funciones auxiliares ---

def leer_lineas(ruta):
    """Devuelve las líneas no vacías de un archivo de texto."""
    # "utf-8-sig" lee bien las tildes y también los archivos guardados como
    # "UTF-8 con BOM" (una opción del Bloc de notas de Windows).
    with open(ruta, "r", encoding="utf-8-sig") as f:
        return [linea.strip() for linea in f if linea.strip()]


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


# --- 4. Programa principal ---

def main():
    # 4.1. Cargar los datos de entrada
    print(f"Cargando {os.path.basename(ARCHIVO_ENTRADA)}...")
    try:
        df = pd.read_excel(ARCHIVO_ENTRADA)
    except FileNotFoundError:
        print(f"Error: no se encuentra {ARCHIVO_ENTRADA}")
        print("Asegúrate de ejecutar primero el Módulo 2.")
        sys.exit(1)

    if "Abstract" not in df.columns:
        print("Error: el Excel no tiene la columna 'Abstract'. ¿Es el articulos.xlsx del Módulo 2?")
        sys.exit(1)

    try:
        preguntas = leer_lineas(ARCHIVO_CLASIFICADOR)
    except FileNotFoundError:
        print(f"Error: no se encontró {os.path.basename(ARCHIVO_CLASIFICADOR)}")
        sys.exit(1)

    if not preguntas:
        print("Error: clasificador.txt está vacío. Escribe una pregunta YES/NO por línea.")
        sys.exit(1)

    print(f"Artículos cargados: {len(df)}")
    print(f"Preguntas cargadas: {len(preguntas)}")

    comprobar_ollama()

    # 4.2. Preparar una columna vacía por pregunta. Se rellenan a medida que
    # el modelo responde; si el proceso se interrumpe, lo pendiente queda vacío.
    for pregunta in preguntas:
        df[pregunta] = ""

    # 4.3. Clasificar cada abstract
    errores_seguidos = 0
    try:
        for indice, fila in df.iterrows():
            titulo = fila.get("Título")
            if pd.isna(titulo):
                titulo = f"Artículo {indice + 1}"
            print(f"\n[{indice + 1}/{len(df)}] {str(titulo)[:50]}...")

            # Si un artículo no tiene abstract (celda vacía), no se le pregunta al modelo.
            abstract = fila.get("Abstract")
            if pd.isna(abstract) or not str(abstract).strip():
                print("    Sin abstract: se salta este artículo.")
                for pregunta in preguntas:
                    df.at[indice, pregunta] = "Sin abstract"
                continue

            for pregunta in preguntas:
                print(f"    Preguntando: {pregunta}")
                respuesta = pedir_a_ollama(abstract, pregunta)
                df.at[indice, pregunta] = respuesta
                if respuesta.startswith("Error"):
                    errores_seguidos += 1
                else:
                    errores_seguidos = 0
                if errores_seguidos >= MAX_ERRORES_SEGUIDOS:
                    break

            if errores_seguidos >= MAX_ERRORES_SEGUIDOS:
                print(f"\nError: Ollama ha fallado {errores_seguidos} veces seguidas; se detiene el proceso.")
                print("Si es por falta de memoria, cierra otros programas y vuelve a intentarlo.")
                break

    except ConnectionError:
        print("\nError: se ha perdido la conexión con Ollama. ¿Se ha cerrado?")
        print("Se guarda lo procesado hasta ahora; lo pendiente queda vacío.")
        print("Si vuelves a ejecutar el script, empezará desde el principio.")
    except KeyboardInterrupt:
        print("\nProceso interrumpido (Ctrl+C).")
        print("Se guarda lo procesado hasta ahora; lo pendiente queda vacío.")
        print("Si vuelves a ejecutar el script, empezará desde el principio.")

    # 4.4. Guardar los resultados
    ruta_guardada = guardar_excel(df, ARCHIVO_SALIDA)
    print(f"\nGuardados {len(df)} artículos clasificados en {os.path.basename(ruta_guardada)}")


if __name__ == "__main__":
    main()
