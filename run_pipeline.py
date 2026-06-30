import sys
from pathlib import Path
from dotenv import load_dotenv

from ingestion.pdf_ingestion import procesar_pdf
from ingestion.structurer import estructurar_documento
from ingestion.chunker import generar_chunks
from ingestion.embedder import embeber_chunks
from db.connection import verificar_conexion

"""
run_pipeline.py

Principal orquestador del flujo. Ejecuta todos los pasos del pipeline, desde la ingesta de un PDF, su estructuracion,
generacion de chunks, hasta la generacion de embeddings y su insercion en la base de datos.
"""

load_dotenv()

def procesar_documento(pdf_path: str) -> None:
    
    path = Path(pdf_path)

    doc = procesar_pdf(path)

    clausulas = estructurar_documento(doc)

    if not clausulas:
        print(f"No se detectaron clausulas en el documento '{pdf_path}'")
        return
    
    chunks = generar_chunks(clausulas)

    embeber_chunks(chunks)

def procesar_directorio(carpeta: str) -> None:

    """
    Funcion encargada de procesar todos los documentos en un directorio con path carpeta

    Params:
- carpeta: string con la ruta a la carpeta que contiene los PDFs a procesar

    Returns:
- None, pero procesa cada PDF en la carpeta y los inserta en la base de datos

    Raises:
- FileNotFoundError si la carpeta no existe
    """
    
    carpeta_path = Path(carpeta)
    pdfs = sorted(carpeta_path.glob("*.pdf"))

    if not pdfs:
        print(f"No se encontraron PDFs en: {carpeta}")
        return
    
    exitosos = 0
    fallidos = []

    for pdf in pdfs:
        try:

            procesar_documento(str(pdf))
            exitosos += 1
        except Exception as e:

            print(f"Error procesando {pdf.name}: {e}")
            fallidos.append(pdf.name)

    print(f"Documentos procesados exitosamente: {exitosos}")
    if fallidos:
        print(f"Documentos con errores: {', '.join(fallidos)}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso:")
        print("  python run_pipeline.py <ruta_pdf>      # un solo PDF")
        print("  python run_pipeline.py <ruta_carpeta>  # carpeta entera")
        sys.exit(1)

    ruta = sys.argv[1]
    path = Path(ruta)

    # verificar conexión a Neon antes de arrancar
    print("Verificando conexión a Neon...")
    verificar_conexion()

    if path.is_dir():
        procesar_directorio(ruta)
    elif path.is_file() and path.suffix.lower() == ".pdf":
        procesar_documento(ruta)
    else:
        print(f"Ruta no válida o no es un PDF: {ruta}")
        sys.exit(1)