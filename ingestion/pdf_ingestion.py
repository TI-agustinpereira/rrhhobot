import fitz          # para leer pdfs digitales

from pathlib import Path
from dataclasses import dataclass

from ingestion.ocr import ocr_pagina   # OCR real para scans (Tesseract)

"""
pdf_ingestion.py

Archivo encargado de procesar los PDFs y devolver texto crudo legible para la LLM encargada de estructurarlo.
"""

MIN_CHARS_DIGITAL = 50 #umbral que uso para considerar si un pdf es digital o scan

#creo estructuras para no manejar diccionarios sueltos
@dataclass
class PageResult:
    page_number: int   # numero de pagina que empieza en 1
    tipo: str          # puede ser digital o escaneada
    texto: str         # el texto extraido



@dataclass
class DocumentResult:
    archivo: str
    paginas: list[PageResult]

    @property
    def texto_completo(self) -> str:
        return "\n\n".join(p.texto for p in self.paginas if p.texto.strip())

    @property
    def resumen(self) -> str:
        digitales = sum(1 for p in self.paginas if p.tipo == "digital")
        escaneadas = sum(1 for p in self.paginas if p.tipo == "escaneada")
        return (
            f"{self.archivo}: {len(self.paginas)} páginas | "
            f"{digitales} digitales, {escaneadas} escaneadas"
        )

def es_pagina_escaneada(pagina: fitz.Page) -> bool:
    """Determina si una pagina es un scan o un pdf digital basado en la cantidad de texto extraido."""

    texto = pagina.get_text().strip()
    return len(texto) < MIN_CHARS_DIGITAL

def extraer_pagina_digital(pagina: fitz.Page) -> str:
    """Extrae el texto de una pagina digital."""

    return pagina.get_text()

def procesar_pdf(pdf_path: str) -> DocumentResult:
    """
    Procesa un pdf y devuelve un DocumentResult con el texto de cada pagina y su tipo.
    
    Params:
- pdf_path: ruta al archivo PDF a procesar

    Returns:
- DocumentResult con el texto extraído de cada página y un resumen del documento

    Raises:
- FileNotFoundError si el archivo no existe
    """

    path = Path(pdf_path)

    if not path.exists():
        raise FileNotFoundError(f"No se encontró el archivo: {pdf_path}")
    if path.suffix.lower() != ".pdf":
        raise ValueError(f"El archivo no es un PDF: {pdf_path}")
    
    doc = fitz.open(pdf_path)
    paginas = []
    for i, pagina in enumerate(doc):
        if es_pagina_escaneada(pagina):
            texto = ocr_pagina(pagina)
            tipo = "escaneada"
        else:
            texto = extraer_pagina_digital(pagina)
            tipo = "digital"

        paginas.append(PageResult(page_number=i+1, tipo=tipo, texto=texto))

    doc.close()
    return DocumentResult(archivo=path.name, paginas=paginas)
