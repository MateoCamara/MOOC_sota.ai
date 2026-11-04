"""
Módulo 3 · Ollama y modelos locales
===================================
Script: run_prompts.py
Se explica en el vídeo 3.3, "Plantillas de Prompting con Salida Verificable (Demo)".

Qué hace
    Rellena tres plantillas de prompting con los datos de tu tema, las envía al
    modelo local deepseek-r1:8b a través de la API REST nativa de Ollama y
    guarda cada respuesta en la carpeta outputs/. Después, validate_outputs.py
    comprueba automáticamente que cada salida tiene el formato que pide su
    plantilla.

Qué tienes que editar
    - TEMA, IDIOMA y AUDIENCIA (más abajo): pon los de tu Proyecto Acumulativo.
    - Si quieres, las plantillas .txt. En cualquiera de ellas puedes usar los
      huecos {TEMA}, {IDIOMA} y {AUDIENCIA}, que se sustituyen por tus valores.

Entradas
    plantilla_a_keywords.txt, plantilla_b_ficha.txt y plantilla_c_sota.txt

Salidas (en la carpeta outputs/)
    tabla_keywords.md   -> tabla Markdown de palabras clave   (Plantilla A)
    ficha_tema.json     -> ficha del tema en JSON             (Plantilla B)
    plan_sota.json      -> plan de mini estado del arte, JSON (Plantilla C)

Cómo ejecutarlo (desde la carpeta principal del repositorio)
    python "modulo 3/run_prompts.py"
    python "modulo 3/validate_outputs.py"

Requisitos
    - Ollama instalado y en marcha (abre la aplicación o ejecuta "ollama serve").
    - El modelo descargado: ollama pull deepseek-r1:8b
"""

import os
import re
import sys

import requests


# --- 1. Configuración ---

DIRECTORIO_SCRIPT = os.path.dirname(os.path.abspath(__file__))
CARPETA_OUTPUTS = os.path.join(DIRECTORIO_SCRIPT, "outputs")

# Dirección de la API REST nativa de Ollama. Ollama escucha en el puerto 11434
# de tu propio ordenador (localhost): el texto no sale de tu máquina.
OLLAMA_URL = "http://localhost:11434/api/chat"
MODELO = "deepseek-r1:8b"

# Variables del tema: cámbialas por las de tu investigación.
TEMA = "tecnicas de estudio basadas en evidencia cientifica"
IDIOMA = "espanol"
AUDIENCIA = "estudiantes universitarios de ingenieria"

# Valores para los huecos {TEMA}, {IDIOMA} y {AUDIENCIA} de las plantillas.
VARIABLES = {"TEMA": TEMA, "IDIOMA": IDIOMA, "AUDIENCIA": AUDIENCIA}


# --- 2. Funciones para hablar con Ollama ---

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


def llamar_ollama(prompt, temperature=0.0):
    """Envía un prompt al modelo y devuelve su respuesta ya limpia.

    temperature=0.0 hace que el modelo sea lo más determinista posible:
    ante el mismo prompt, respuestas casi idénticas. Es lo que queremos
    cuando necesitamos un formato fijo y verificable.
    """
    peticion = {
        "model": MODELO,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,  # Esperar a la respuesta completa en lugar de recibirla a trozos
        "options": {
            "temperature": temperature,
            "num_predict": 2048,  # Máximo de tokens que puede generar el modelo
        },
    }

    try:
        # timeout: segundos máximos de espera. En un ordenador sin GPU el
        # modelo puede tardar varios minutos en contestar.
        respuesta = requests.post(OLLAMA_URL, json=peticion, timeout=900)
    except requests.exceptions.ConnectionError:
        print("\nError: no se puede conectar con Ollama en http://localhost:11434")
        print("Arranca Ollama (abre la aplicación o ejecuta 'ollama serve') y vuelve a intentarlo.")
        sys.exit(1)
    except requests.exceptions.Timeout:
        print("\nError: Ollama ha tardado demasiado en responder. Vuelve a intentarlo.")
        sys.exit(1)

    if respuesta.status_code == 404:
        # 404 = Ollama no encuentra el modelo: no está descargado.
        print(f"\nError de Ollama: {respuesta.text}")
        print(f"Descarga el modelo con: ollama pull {MODELO}")
        sys.exit(1)
    if respuesta.status_code != 200:
        # Otros errores; el más habitual es la falta de memoria.
        print(f"\nError de Ollama ({respuesta.status_code}): {respuesta.text}")
        print("Si es por falta de memoria, cierra otros programas y vuelve a intentarlo.")
        sys.exit(1)

    datos = respuesta.json()
    if datos.get("done_reason") == "length":
        # El modelo ha llegado a num_predict antes de terminar.
        print("    Aviso: la respuesta se ha cortado por llegar al límite num_predict.")
    return limpiar_respuesta(datos["message"]["content"])


# --- 3. Ejecutar una plantilla ---

def ejecutar_plantilla(nombre, archivo_plantilla, archivo_salida):
    """Rellena una plantilla, la envía a Ollama y guarda la respuesta.

    nombre:            texto que se muestra por pantalla
    archivo_plantilla: archivo .txt con el prompt y los huecos {VARIABLE}
    archivo_salida:    nombre del archivo que se crea dentro de outputs/
    """
    print(f">>> Ejecutando {nombre}...")

    # "utf-8-sig" lee bien las tildes y también los archivos guardados como
    # "UTF-8 con BOM" (una opción del Bloc de notas de Windows).
    with open(os.path.join(DIRECTORIO_SCRIPT, archivo_plantilla), "r", encoding="utf-8-sig") as f:
        prompt = f.read()

    # Sustituir cada hueco {VARIABLE} por su valor
    for clave, valor in VARIABLES.items():
        prompt = prompt.replace("{" + clave + "}", valor)

    resultado = llamar_ollama(prompt)

    with open(os.path.join(CARPETA_OUTPUTS, archivo_salida), "w", encoding="utf-8") as f:
        f.write(resultado)
    print(f"    Guardado en outputs/{archivo_salida}")


# --- 4. Programa principal ---

def main():
    os.makedirs(CARPETA_OUTPUTS, exist_ok=True)  # Crea outputs/ si no existe

    # Plantilla A: palabras clave en una tabla Markdown
    ejecutar_plantilla("Plantilla A (keywords)", "plantilla_a_keywords.txt", "tabla_keywords.md")

    # Plantilla B: ficha del tema en JSON
    ejecutar_plantilla("Plantilla B (ficha del tema)", "plantilla_b_ficha.txt", "ficha_tema.json")

    # Plantilla C: plan de mini estado del arte en JSON
    ejecutar_plantilla("Plantilla C (plan mini-SOTA)", "plantilla_c_sota.txt", "plan_sota.json")

    print("\n>>> Todas las plantillas ejecutadas. Revisa la carpeta outputs/")
    print('>>> Siguiente paso: python "modulo 3/validate_outputs.py"')


if __name__ == "__main__":
    main()
