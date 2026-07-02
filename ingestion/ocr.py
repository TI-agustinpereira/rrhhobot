import fitz
import pytesseract
from PIL import Image

"""
ocr.py

Modulo de OCR para paginas escaneadas (imagenes sin capa de texto).

Reemplaza a pymupdf4llm para el path de scans. Cuando una pagina es una imagen
pura (get_text() devuelve 0 caracteres), pymupdf4llm la omite con un marcador
del tipo '==> picture [...] intentionally omitted <=='.

Aca renderizamos la pagina a imagen y la pasamos por Tesseract. Ademas recortamos
el margen derecho antes de OCRear: en los contratos/actas tipicos, las firmas y
rubricas manuscritas caen en ese margen, y recortandolas en origen evitamos que
contaminen el texto que luego se estructura en clausulas.
"""

# Configuracion ------------------------------------------------------------

OCR_DPI = 550            # resolucion de render
OCR_LANG = "spa"         # idioma de Tesseract (requiere el traineddata 'spa' instalado)
MARGEN_DERECHO = 0.82    # se descarta todo lo que este a la derecha de este % del ancho (firmas/rubricas)
MARGEN_INFERIOR = 1.0    # idem para el pie de pagina (1.0 = no recortar; bajar si el pie trae firmas)

# Si Tesseract no quedo en el PATH del sistema, descomentar y apuntar al binario:
pytesseract.pytesseract.tesseract_cmd = r"C:/Users/agupereira/AppData/Local/Programs/Tesseract-OCR/tesseract.exe"


def ocr_pagina(pagina: fitz.Page) -> str:
    """
    OCRea una pagina escaneada, recortando los margenes para excluir firmas.

    Params:
- pagina: objeto fitz.Page ya abierto (se reutiliza el documento del caller,
          asi no se reabre el PDF por cada pagina).

    Returns:
- el texto reconocido por Tesseract en la region central de la pagina.

    Raises:
- RuntimeError si Tesseract no esta instalado o no se encuentra el binario.
    """

    rect = pagina.rect

    # region a OCRear: pagina completa menos los margenes configurados
    clip = fitz.Rect(
        rect.x0,
        rect.y0,
        rect.width * MARGEN_DERECHO,
        rect.height * MARGEN_INFERIOR,
    )

    # pix = pagina.get_pixmap(dpi=OCR_DPI, clip=clip)
    # modo = "RGBA" if pix.alpha else "RGB"
    # img = Image.frombytes(modo, (pix.width, pix.height), pix.samples)
    
    pix = pagina.get_pixmap(dpi=OCR_DPI, clip=clip)
    modo = "RGBA" if pix.alpha else "RGB"
    img = Image.frombytes(modo, (pix.width, pix.height), pix.samples)
    img = img.convert("L")   # escala de grises: ayuda a Tesseract con glifos pequeños

    try:
        return pytesseract.image_to_string(img, lang=OCR_LANG)
    except pytesseract.TesseractNotFoundError as e:
        raise RuntimeError(
            "No se encontro el binario de Tesseract. Instalalo (en Windows, el build "
            "de UB-Mannheim con el idioma Spanish) y, si no quedo en el PATH, seteá "
            "pytesseract.pytesseract.tesseract_cmd en ingestion/ocr.py."
        ) from e
