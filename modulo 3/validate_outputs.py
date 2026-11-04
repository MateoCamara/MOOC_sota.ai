"""
Módulo 3 · Ollama y modelos locales
===================================
Script: validate_outputs.py
Se explica en el vídeo 3.3, "Plantillas de Prompting con Salida Verificable (Demo)".

Qué hace
    Comprueba de forma automática que las salidas de run_prompts.py tienen el
    formato que pedía cada plantilla. Para cada archivo da un resultado
    PASS (correcto) o FAIL (incorrecto, con el motivo):

        outputs/tabla_keywords.md -> es una tabla Markdown con las columnas Grupo | Termino | Nota
        outputs/ficha_tema.json   -> es un JSON válido con todas las claves de la Plantilla B
        outputs/plan_sota.json    -> es un JSON válido con todas las claves de la Plantilla C

    Así se comprueba que la salida de un modelo de IA cumple un contrato de
    formato antes de usarla en el siguiente paso. Un FAIL no es un fallo del
    script: significa que el modelo no ha respetado el formato pedido. Vuelve a
    ejecutar run_prompts.py o refuerza las instrucciones de la plantilla.

Qué tienes que editar
    Si cambias las plantillas, actualiza aquí las columnas o claves esperadas.

Entradas
    outputs/tabla_keywords.md, outputs/ficha_tema.json y outputs/plan_sota.json

Salidas
    outputs/verificacion.md -> el resumen PASS/FAIL de las tres comprobaciones.

Cómo ejecutarlo (después de run_prompts.py)
    python "modulo 3/validate_outputs.py"
"""

import json
import os


# --- 1. Configuración ---

DIRECTORIO_SCRIPT = os.path.dirname(os.path.abspath(__file__))
CARPETA_OUTPUTS = os.path.join(DIRECTORIO_SCRIPT, "outputs")

# Lo que exige cada plantilla. Si cambias una plantilla, cámbialo también aquí.
COLUMNAS_TABLA = ["Grupo", "Termino", "Nota"]
CLAVES_FICHA = ["tema", "audiencia", "objetivo", "alcance",
                "subpreguntas", "palabras_clave", "riesgos_y_sesgos"]
CLAVES_PLAN = ["titulo", "resumen_100_palabras", "secciones",
               "criterios_de_calidad"]


# --- 2. Validadores ---

def validar_tabla_markdown(nombre_archivo, columnas_esperadas):
    """Comprueba que el archivo contiene una tabla Markdown con esas columnas."""
    try:
        with open(os.path.join(CARPETA_OUTPUTS, nombre_archivo), "r", encoding="utf-8-sig") as f:
            tabla = f.read()
    except FileNotFoundError:
        return f"FAIL: No se encontró outputs/{nombre_archivo}"

    # Nos quedamos con las líneas de la tabla (las que tienen "|"), sin la
    # línea separadora |---|---|.
    lineas = [linea for linea in tabla.strip().split("\n") if "|" in linea and "---" not in linea]
    if not lineas:
        return "FAIL: No se encontró una tabla Markdown válida"

    # La primera línea de la tabla es la cabecera: "| Grupo | Termino | Nota |"
    cabecera = [celda.strip() for celda in lineas[0].split("|") if celda.strip()]
    if all(columna in cabecera for columna in columnas_esperadas):
        return "PASS: Tabla Markdown con columnas correctas"
    return f"FAIL: Columnas esperadas {columnas_esperadas}, encontradas {cabecera}"


def validar_json(nombre_archivo, claves_obligatorias, descripcion):
    """Comprueba que el archivo es un JSON válido y tiene todas las claves."""
    try:
        with open(os.path.join(CARPETA_OUTPUTS, nombre_archivo), "r", encoding="utf-8-sig") as f:
            datos = json.load(f)  # Falla si el texto no es un JSON correcto
    except FileNotFoundError:
        return f"FAIL: No se encontró outputs/{nombre_archivo}"
    except json.JSONDecodeError as e:
        return f"FAIL: {nombre_archivo} no es un JSON válido — {e}"

    if not isinstance(datos, dict):
        return f"FAIL: {nombre_archivo} debería ser un objeto JSON {{...}}"

    faltantes = [clave for clave in claves_obligatorias if clave not in datos]
    if not faltantes:
        return f"PASS: JSON {descripcion} válido con todas las claves"
    return f"FAIL: Faltan claves en {nombre_archivo}: {faltantes}"


# --- 3. Programa principal ---

def main():
    resultados = []

    print(">>> Validando tabla_keywords.md (Plantilla A)...")
    resultados.append(validar_tabla_markdown("tabla_keywords.md", COLUMNAS_TABLA))
    print(f"    {resultados[-1]}")

    print(">>> Validando ficha_tema.json (Plantilla B)...")
    resultados.append(validar_json("ficha_tema.json", CLAVES_FICHA, "ficha del tema"))
    print(f"    {resultados[-1]}")

    print(">>> Validando plan_sota.json (Plantilla C)...")
    resultados.append(validar_json("plan_sota.json", CLAVES_PLAN, "plan mini-SOTA"))
    print(f"    {resultados[-1]}")

    # Resumen por pantalla
    print("\n" + "=" * 50)
    print("RESUMEN DE VALIDACIÓN")
    print("=" * 50)
    for resultado in resultados:
        print(f"  {resultado}")

    # Guardar el resumen en outputs/verificacion.md
    os.makedirs(CARPETA_OUTPUTS, exist_ok=True)
    with open(os.path.join(CARPETA_OUTPUTS, "verificacion.md"), "w", encoding="utf-8") as f:
        f.write("# Resultado de validación\n\n")
        f.write("\n".join(f"- {resultado}" for resultado in resultados))
        f.write("\n")
    print("\nResultado guardado en outputs/verificacion.md")


if __name__ == "__main__":
    main()
