## Comandos útiles

```powershell
# Ingesta local
python run_pipeline.py "docs/archivo.pdf"     # un PDF
python run_pipeline.py docs/                   # carpeta entera

# Levantar la web local
uvicorn api.main:app --reload                  # http://127.0.0.1:8000/

# Consulta por CLI
python -m rag.generator "mi pregunta"
```