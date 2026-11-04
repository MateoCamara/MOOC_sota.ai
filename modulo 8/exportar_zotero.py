"""
Módulo 8 · Gestión bibliográfica y Zotero
=========================================
Script: exportar_zotero.py
Se explica en el vídeo 8.3, "Del Pipeline a Zotero — Exportación y Gestión Bibliográfica (Demo)".

Qué hace
    Cierra el pipeline del curso: sube a tu biblioteca de Zotero los artículos
    que seleccionaste en el Módulo 5.
    1. Lee tu configuración (biblioteca y API key) de zotero_config.txt.
    2. Se conecta a tu biblioteca de Zotero a través de su API web.
    3. Lee articulos_clasificacion_final.xlsx (salida del Módulo 5) y, para
       cada artículo que pasó el filtro (columna "Pasa filtro" = YES):
         - crea un ítem de tipo "Preprint" con título, autores, fecha,
           abstract, URL, DOI e identificador de arXiv;
         - le añade una nota con las respuestas que dio el modelo en el Módulo 5;
         - le pone la etiqueta "sota-ai" para que lo encuentres fácilmente.
    4. Si un artículo ya se subió en una ejecución anterior (mismo título y
       etiqueta "sota-ai"), lo salta para no crear duplicados.

Qué tienes que editar
    - zotero_config.txt: tu library_id, library_type y api_key (y, si quieres,
      la collection_key de la colección donde guardar los artículos). Dentro
      del archivo se explica cómo conseguir cada dato.
    - SIMULAR (más abajo): ponlo a True para ver qué se subiría sin tocar
      tu biblioteca.

Entradas
    zotero_config.txt
    ../modulo 5/articulos_clasificacion_final.xlsx   (salida del Módulo 5)
    ../modulo 5/clasificador_articulo.txt            (para saber qué columnas van a la nota)

Salidas
    Los ítems nuevos en tu biblioteca de Zotero (https://www.zotero.org).

Cómo ejecutarlo (desde la carpeta principal del repositorio)
    python "modulo 8/exportar_zotero.py"

Requisitos
    Conexión a Internet y una cuenta de Zotero con una API key con permiso de escritura.
"""

import html
import os
import re
import sys

import pandas as pd
from pyzotero import zotero, zotero_errors


# Si la terminal no puede mostrar algún carácter (por ejemplo, una letra griega
# de un título), se muestra "?" en lugar de detener el programa con un error.
sys.stdout.reconfigure(errors="replace")


# --- 1. Configuración ---

DIRECTORIO_SCRIPT = os.path.dirname(os.path.abspath(__file__))

ARCHIVO_CONFIG = os.path.join(DIRECTORIO_SCRIPT, "zotero_config.txt")
ARCHIVO_ENTRADA = os.path.join(DIRECTORIO_SCRIPT, "..", "modulo 5", "articulos_clasificacion_final.xlsx")
ARCHIVO_PREGUNTAS_M5 = os.path.join(DIRECTORIO_SCRIPT, "..", "modulo 5", "clasificador_articulo.txt")

# Columna que crea el Módulo 5 para marcar los artículos seleccionados.
COLUMNA_FILTRO = "Pasa filtro"

# Etiqueta que se pone a todo lo que sube este script.
ETIQUETA = "sota-ai"

# True = solo mostrar qué se subiría, sin escribir nada en Zotero.
SIMULAR = False


# --- 2. Leer archivos de texto ---

def cargar_config(ruta):
    """Lee zotero_config.txt y devuelve un diccionario {clave: valor}.

    Se ignoran las líneas vacías y las que empiezan por # (comentarios).
    """
    config = {}
    # "utf-8-sig" lee bien las tildes y también los archivos guardados como
    # "UTF-8 con BOM" (una opción del Bloc de notas de Windows).
    with open(ruta, "r", encoding="utf-8-sig") as f:
        for linea in f:
            linea = linea.strip()
            if not linea or linea.startswith("#") or "=" not in linea:
                continue
            clave, valor = linea.split("=", 1)
            # Se quitan espacios y comillas por si alguien escribe api_key = "abc"
            config[clave.strip()] = valor.strip().strip("\"'")
    return config


def leer_lineas(ruta):
    """Devuelve las líneas no vacías de un archivo de texto, o [] si no existe."""
    try:
        with open(ruta, "r", encoding="utf-8-sig") as f:
            return [linea.strip() for linea in f if linea.strip()]
    except FileNotFoundError:
        return []


# --- 3. Preparar los datos de cada artículo ---

def texto_o_vacio(valor):
    """Convierte una celda del Excel en texto. Las celdas vacías pasan a ""."""
    if pd.isna(valor):
        return ""
    return str(valor).strip()


def normalizar_titulo(titulo):
    """Pasa el título a minúsculas y sin espacios repetidos, para compararlo."""
    return " ".join(titulo.lower().split())


def autores_a_creators(autores):
    """Convierte "Ana García; John Smith" en la lista de autores que espera Zotero.

    Se toma la última palabra como apellido y el resto como nombre. No acierta
    con apellidos compuestos ("de la Fuente"): revísalos luego en Zotero.
    """
    creators = []
    for autor in autores.split(";"):
        autor = autor.strip()
        if not autor:
            continue
        partes = autor.rsplit(" ", 1)  # Separa por el último espacio
        if len(partes) == 2:
            nombre, apellido = partes
        else:
            nombre, apellido = "", autor
        creators.append({"creatorType": "author", "firstName": nombre, "lastName": apellido})
    return creators


def arxiv_id_desde_url(url):
    """Saca el identificador de arXiv de su URL.

    "http://arxiv.org/abs/2301.12345v2" -> "2301.12345" (sin la versión)
    """
    coincidencia = re.search(r"arxiv\.org/abs/(.+?)(v\d+)?$", url)
    return coincidencia.group(1) if coincidencia else ""


def limpiar_doi(doi):
    """Devuelve el DOI, o "" si el Excel dice que no hay ("No disponible")."""
    doi = texto_o_vacio(doi).rstrip(".")  # Quita un punto final que a veces se cuela
    if doi.lower() in ("", "no disponible", "doi no disponible", "nan"):
        return ""
    return doi


def crear_nota_html(fila, preguntas):
    """Crea el texto de la nota de Zotero con las respuestas del Módulo 5.

    Zotero guarda las notas en HTML. html.escape() evita que símbolos como
    < o & de las respuestas rompan el formato.
    """
    partes = []
    for pregunta in preguntas:
        respuesta = texto_o_vacio(fila.get(pregunta))
        # Las celdas vacías y los errores de Ollama no van a la nota.
        if respuesta and not respuesta.startswith("Error"):
            respuesta_html = html.escape(respuesta).replace("\n", "<br>")
            partes.append(f"<p><strong>{html.escape(pregunta)}</strong><br>{respuesta_html}</p>")
    if not partes:
        return ""

    cabecera = (
        "<h2>Análisis automático (Módulo 5)</h2>"
        "<p><em>Respuestas generadas por un modelo de IA a partir del PDF. "
        "Contrástalas con el artículo antes de citarlas (Módulo 6).</em></p>"
    )
    return cabecera + "".join(partes)


def ya_subido(zot, titulo):
    """Devuelve True si en la biblioteca ya hay un ítem con este título y la etiqueta del script.

    Solo se miran los ítems con la etiqueta "sota-ai", es decir, los que
    subió este script. Lo que hayas importado a mano no cuenta.
    """
    encontrados = zot.items(q=titulo, tag=ETIQUETA, limit=25)
    for item in encontrados:
        if normalizar_titulo(item["data"].get("title", "")) == normalizar_titulo(titulo):
            return True
    return False


def crear_item(zot, fila, collection_key):
    """Prepara el ítem de Zotero (tipo Preprint) a partir de una fila del Excel."""
    item = zot.item_template("preprint")  # Plantilla vacía con los campos de un preprint

    url = texto_o_vacio(fila.get("URL"))
    arxiv_id = arxiv_id_desde_url(url)

    item["title"] = texto_o_vacio(fila.get("Título"))
    item["creators"] = autores_a_creators(texto_o_vacio(fila.get("Autores")))
    item["abstractNote"] = texto_o_vacio(fila.get("Abstract"))
    item["date"] = texto_o_vacio(fila.get("Fecha"))
    item["url"] = url
    item["repository"] = "arXiv"
    item["libraryCatalog"] = "arXiv.org"
    if arxiv_id:
        item["archiveID"] = f"arXiv:{arxiv_id}"

    # Si el artículo tiene DOI (de la revista donde se publicó), se usa ese.
    # Si no, se usa el DOI que arXiv asigna a todos sus preprints.
    doi = limpiar_doi(fila.get("DOI"))
    if doi:
        item["DOI"] = doi
    elif arxiv_id:
        item["DOI"] = f"10.48550/arXiv.{arxiv_id}"

    item["tags"] = [{"tag": ETIQUETA}]
    if collection_key:
        item["collections"] = [collection_key]
    return item


# --- 4. Programa principal ---

def main():
    print("--- Módulo 8: exportación a Zotero ---")

    # 4.1. Cargar y comprobar la configuración
    try:
        config = cargar_config(ARCHIVO_CONFIG)
    except FileNotFoundError:
        print(f"Error: no se encontró {os.path.basename(ARCHIVO_CONFIG)} junto a este script.")
        sys.exit(1)

    claves_necesarias = ["library_id", "library_type", "api_key"]
    faltan = [clave for clave in claves_necesarias if not config.get(clave)]
    sin_rellenar = [clave for clave in claves_necesarias if config.get(clave, "").startswith("TU_")]
    if faltan or sin_rellenar:
        print("Error: completa zotero_config.txt antes de ejecutar el script.")
        print(f"  Claves que faltan: {faltan}" if faltan else f"  Claves sin rellenar: {sin_rellenar}")
        print("  Dentro del archivo se explica cómo conseguir cada dato.")
        sys.exit(1)

    # Las claves de colección de Zotero van en mayúsculas (por ejemplo, ABCD1234).
    collection_key = config.get("collection_key", "").upper()
    if collection_key.startswith("TU_"):
        collection_key = ""  # Sigue con el valor de ejemplo: se ignora

    # 4.2. Conectar con Zotero
    zot = zotero.Zotero(config["library_id"], config["library_type"], config["api_key"])
    try:
        print(f"Conectado a Zotero. Ítems en la biblioteca: {zot.count_items()}")
        if collection_key:
            coleccion = zot.collection(collection_key)
            print(f"Los artículos se guardarán en la colección: {coleccion['data']['name']}")
    except zotero_errors.UserNotAuthorisedError:
        print("Error: Zotero rechaza la API key. Revisa api_key y library_id en zotero_config.txt.")
        sys.exit(1)
    except zotero_errors.ResourceNotFoundError:
        print("Error: Zotero no encuentra la biblioteca o la colección. "
              "Revisa library_id, library_type y collection_key.")
        sys.exit(1)
    except Exception as e:
        print(f"Error conectando a Zotero: {e}")
        print("Comprueba tu conexión a Internet.")
        sys.exit(1)

    # 4.3. Cargar el Excel del Módulo 5
    try:
        df = pd.read_excel(ARCHIVO_ENTRADA)
    except FileNotFoundError:
        print(f"Error: no se encuentra {os.path.basename(ARCHIVO_ENTRADA)}")
        print("Asegúrate de ejecutar primero el Módulo 5.")
        sys.exit(1)

    # Solo se suben los artículos que pasaron el filtro del Módulo 5.
    if COLUMNA_FILTRO not in df.columns:
        print(f"Error: el Excel no tiene la columna '{COLUMNA_FILTRO}'.")
        print("Parece de una versión antigua: vuelve a ejecutar el Módulo 5.")
        sys.exit(1)

    df = df[df[COLUMNA_FILTRO].astype(str).str.strip().str.upper() == "YES"]
    print(f"Artículos que pasaron el filtro del Módulo 5: {len(df)}")
    if df.empty:
        print("No hay nada que subir. Revisa discriminador.txt en el Módulo 5 y vuelve a ejecutarlo.")
        return

    # Las preguntas del Módulo 5 son columnas del Excel: van a la nota de cada artículo.
    preguntas = [p for p in leer_lineas(ARCHIVO_PREGUNTAS_M5) if p in df.columns]

    if SIMULAR:
        print("\nMODO SIMULACIÓN: no se escribirá nada en Zotero.")

    # 4.4. Subir cada artículo
    subidos, saltados, fallos = 0, 0, 0
    titulos_vistos = set()  # Para no subir dos veces un título repetido en el Excel
    numero = 0  # Contador para mostrar el progreso [1/N], [2/N]...

    for _, fila in df.iterrows():
        numero += 1
        titulo = texto_o_vacio(fila.get("Título")) or "Sin título"
        print(f"\n[{numero}/{len(df)}] {titulo[:60]}...")

        if normalizar_titulo(titulo) in titulos_vistos:
            print("    Título repetido en el Excel: se salta.")
            saltados += 1
            continue
        titulos_vistos.add(normalizar_titulo(titulo))

        try:
            if ya_subido(zot, titulo):
                print("    Ya estaba en Zotero (subido antes por este script): se salta.")
                saltados += 1
                continue

            item = crear_item(zot, fila, collection_key)
            nota = crear_nota_html(fila, preguntas)

            if SIMULAR:
                print(f"    Se subiría con {len(item['creators'])} autores"
                      f"{' y una nota con el análisis' if nota else ''}.")
                subidos += 1
                continue

            respuesta = zot.create_items([item])
            if not respuesta.get("successful"):
                print(f"    Fallo: {respuesta.get('failed')}")
                fallos += 1
                continue

            # La respuesta de Zotero incluye la clave (key) del ítem nuevo;
            # la usamos para colgar la nota de ese ítem.
            clave_item = respuesta["successful"]["0"]["key"]
            print("    Subido correctamente.")
            subidos += 1

            if nota:
                plantilla_nota = zot.item_template("note")
                plantilla_nota["note"] = nota
                plantilla_nota["tags"] = [{"tag": ETIQUETA}]
                respuesta_nota = zot.create_items([plantilla_nota], parentid=clave_item)
                if respuesta_nota.get("successful"):
                    print("    Nota con el análisis del Módulo 5 añadida.")
                else:
                    print(f"    No se pudo añadir la nota: {respuesta_nota.get('failed')}")

        except zotero_errors.UserNotAuthorisedError:
            print("\nError: la API key no tiene permiso de escritura.")
            print("Edita la clave en https://www.zotero.org/settings/keys y marca 'Allow write access'.")
            sys.exit(1)
        except Exception as e:
            print(f"    Error: {e}")
            fallos += 1

    # 4.5. Resumen
    print(f"\n{'=' * 50}")
    if SIMULAR:
        print(f"SIMULACIÓN: se subirían {subidos}, {saltados} ya existían o se repetían, {fallos} fallos")
        print("Pon SIMULAR = False para subirlos de verdad.")
    else:
        print(f"RESUMEN: {subidos} subidos, {saltados} ya existían o se repetían, {fallos} fallos")
    print(f"{'=' * 50}")
    if subidos and not SIMULAR:
        print("Consejo: en Zotero, filtra por la etiqueta 'sota-ai' para ver lo importado y")
        print("revisa los metadatos (autores, fecha, DOI) antes de citar. Si un preprint se")
        print("publicó después en una revista, importa la versión publicada con su DOI")
        print("(botón 'Añadir ítem por identificador', la varita mágica de Zotero).")


if __name__ == "__main__":
    main()
