"""
Módulo 2 · Búsqueda y evaluación de fuentes
===========================================
Script: descargar_articulos_arxiv.py
Se explica en el vídeo 2.4, "Descarga de Artículos desde arXiv (Demo Práctica)".

Qué hace
    1. Lee tu cadena de búsqueda del archivo query.txt.
    2. Busca en arXiv los artículos más relevantes para esa búsqueda.
    3. Descarga el PDF de cada artículo en la carpeta pdfs/ (1.pdf, 2.pdf, ...).
    4. Guarda los metadatos de cada artículo (título, autores, fecha, abstract,
       DOI, URL y ruta del PDF) en articulos.xlsx.

Qué tienes que editar
    - query.txt: escribe ahí la cadena de búsqueda de TU tema.
      arXiv admite AND, OR, ANDNOT, comillas para frases exactas y paréntesis,
      por ejemplo:  ("plant disease" OR "leaf disease") AND detection
    - MAX_RESULTADOS (más abajo): cuántos artículos quieres descargar.

Entradas
    query.txt

Salidas
    articulos.xlsx      -> una fila por artículo. Es la entrada del Módulo 4.
    pdfs/<Indice>.pdf   -> los PDFs descargados. Los usa el Módulo 5.

Cómo ejecutarlo (desde la carpeta principal del repositorio)
    python "modulo 2/descargar_articulos_arxiv.py"

Requisitos
    Conexión a Internet y las librerías de requirements.txt
    (pip install -r requirements.txt).
"""

import os
import sys
import time
from datetime import datetime

import arxiv
import pandas as pd
import requests


# Si la terminal no puede mostrar algún carácter (por ejemplo, una letra griega
# de un título), se muestra "?" en lugar de detener el programa con un error.
sys.stdout.reconfigure(errors="replace")


# --- 1. Configuración ---

# Carpeta donde está este script. Todas las rutas se construyen a partir de
# ella para que el script funcione lo ejecutes desde donde lo ejecutes.
DIRECTORIO_SCRIPT = os.path.dirname(os.path.abspath(__file__))

ARCHIVO_QUERY = os.path.join(DIRECTORIO_SCRIPT, "query.txt")
CARPETA_PDFS = os.path.join(DIRECTORIO_SCRIPT, "pdfs")
ARCHIVO_SALIDA = os.path.join(DIRECTORIO_SCRIPT, "articulos.xlsx")

# Número máximo de artículos que se descargan. Empieza con pocos: en los
# módulos 4 y 5 el modelo de IA tendrá que leer cada uno de ellos.
MAX_RESULTADOS = 20

# Segundos de espera entre una descarga de PDF y la siguiente. arXiv pide no
# saturar sus servidores con peticiones seguidas: respétalo.
PAUSA_ENTRE_DESCARGAS = 3


# --- 2. Funciones auxiliares ---

def leer_query(ruta):
    """Lee la cadena de búsqueda de query.txt y la devuelve en una sola línea."""
    try:
        # "utf-8-sig" lee bien las tildes y también los archivos guardados como
        # "UTF-8 con BOM" (una opción del Bloc de notas de Windows).
        with open(ruta, "r", encoding="utf-8-sig") as f:
            return f.read().replace("\n", " ").strip()
    except FileNotFoundError:
        print(f"Error: no se encontró el archivo {os.path.basename(ruta)}")
        print("Crea un archivo query.txt junto a este script con tu cadena de búsqueda.")
        sys.exit(1)


def limpiar_espacios(texto):
    """Quita saltos de línea y espacios repetidos.

    arXiv devuelve títulos y abstracts con saltos de línea en mitad de las
    frases; así quedan en una sola línea y se leen mejor en Excel.
    """
    return " ".join(str(texto).split())


def descargar_pdf(url_pdf, ruta_destino):
    """Descarga el PDF de url_pdf y lo guarda en ruta_destino.

    Devuelve True si la descarga ha ido bien y False si no.
    """
    # Si hay un PDF antiguo con este nombre (de una búsqueda anterior), se borra
    # antes de descargar. Si no, cuando una descarga fallara, el Módulo 5 leería
    # el PDF de otro artículo.
    if os.path.exists(ruta_destino):
        os.remove(ruta_destino)

    try:
        respuesta = requests.get(url_pdf, timeout=60)
        respuesta.raise_for_status()  # Lanza un error si arXiv responde 404, 500...
    except requests.exceptions.RequestException as e:
        print(f"     Error descargando el PDF: {e}")
        return False

    # Un PDF de verdad siempre empieza por "%PDF". Si no, arXiv nos ha devuelto
    # otra cosa (por ejemplo, una página de error) y no la guardamos.
    if not respuesta.content.startswith(b"%PDF"):
        print("     Error: lo descargado no es un PDF válido.")
        return False

    with open(ruta_destino, "wb") as f:  # "wb": escribir en modo binario
        f.write(respuesta.content)
    return True


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


# --- 3. Programa principal ---

def main():
    # 3.1. Leer la búsqueda
    query = leer_query(ARCHIVO_QUERY)
    if not query:
        print("Error: query.txt está vacío. Escribe en él tu cadena de búsqueda.")
        sys.exit(1)
    print(f"Buscando en arXiv: {query}")

    # 3.2. Buscar en arXiv
    # El cliente ya espera unos segundos entre peticiones a la API de arXiv
    # y reintenta automáticamente si hay un fallo puntual.
    cliente = arxiv.Client()
    busqueda = arxiv.Search(
        query=query,
        max_results=MAX_RESULTADOS,
        sort_by=arxiv.SortCriterion.Relevance,  # Primero, los más relevantes
    )
    try:
        resultados = list(cliente.results(busqueda))
    except Exception as e:
        print(f"Error al buscar en arXiv: {e}")
        print("Comprueba tu conexión a Internet y la sintaxis de query.txt.")
        sys.exit(1)

    print(f"Se encontraron {len(resultados)} resultados.")
    if not resultados:
        print("Prueba con una búsqueda más amplia (menos términos o más sinónimos con OR).")
        print("OJO: articulos.xlsx NO se ha actualizado. Si existía, sigue siendo el de la búsqueda anterior.")
        sys.exit(1)

    # 3.3. Recorrer los resultados: descargar el PDF y anotar los metadatos
    os.makedirs(CARPETA_PDFS, exist_ok=True)  # Crea pdfs/ si no existe
    filas = []
    pdfs_descargados = 0

    # enumerate(..., 1) numera los artículos empezando en 1. Ese número es el
    # "Indice" que relaciona cada fila del Excel con su PDF (1 -> pdfs/1.pdf).
    for indice, resultado in enumerate(resultados, 1):
        titulo = limpiar_espacios(resultado.title)
        print(f"[{indice}/{len(resultados)}] {titulo[:60]}...")

        # Las versiones nuevas de la librería arxiv ya no descargan PDFs, pero
        # sí dan su dirección (pdf_url). Si faltara, se deduce de la URL del artículo.
        url_pdf = resultado.pdf_url or resultado.entry_id.replace("/abs/", "/pdf/")
        nombre_pdf = f"{indice}.pdf"

        if descargar_pdf(url_pdf, os.path.join(CARPETA_PDFS, nombre_pdf)):
            archivo_pdf = f"pdfs/{nombre_pdf}"
            pdfs_descargados += 1
            print(f"     PDF descargado: {archivo_pdf}")
        else:
            archivo_pdf = ""  # Vacío = no hay PDF para este artículo

        filas.append({
            "Indice": indice,
            "Título": titulo,
            # arXiv da una lista de autores; los unimos con "; " en una celda.
            "Autores": "; ".join(autor.name for autor in resultado.authors),
            "Fecha": resultado.published.strftime("%Y-%m-%d"),  # Fecha de la 1.ª versión
            "Año": resultado.published.year,
            "Abstract": limpiar_espacios(resultado.summary),
            # DOI de la versión publicada en revista, si los autores lo indicaron.
            # Muchos preprints de arXiv aún no lo tienen. rstrip(".") quita un
            # punto final que a veces se cuela al copiarlo.
            "DOI": (resultado.doi or "").strip().rstrip(".") or "No disponible",
            "URL": resultado.entry_id,  # Página del artículo en arXiv
            "Archivo PDF": archivo_pdf,
        })

        if indice < len(resultados):  # No hace falta esperar tras el último
            time.sleep(PAUSA_ENTRE_DESCARGAS)

    # 3.4. Guardar los metadatos en Excel
    df = pd.DataFrame(filas)
    ruta_guardada = guardar_excel(df, ARCHIVO_SALIDA)
    print(f"\nGuardados {len(filas)} artículos en {os.path.basename(ruta_guardada)}")
    print(f"PDFs descargados: {pdfs_descargados} de {len(filas)} (carpeta pdfs/)")


# Este bloque hace que main() solo se ejecute al lanzar el script directamente
# (python descargar_articulos_arxiv.py) y no si otro script lo importa.
if __name__ == "__main__":
    main()
