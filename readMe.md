Chatbot para RRHH y RRLL: RRHHobot

Ingiere los documentos .pdf que estan en docs/ y los procesa. Por proceso se entiende que se cumple el pipeline de principio a fin:

        1. los documentos son procesados por librerias PyMuPDF, PyMuPDF4LLM y tesseract en pdf_ingestion.procesar_pdf(path) para poder ser leidos por lenguaje de maquina

        2. los documentos procesados se envian a un modelo de OpenAI (gpt-4o-mini) para ser estructurados y permitir manejar formatos variados en structurer.estructurar_documento(DocumentResult), devolviendo una lista de objetos Clausula para usar mas adelante.

        3. con estas clausulas se generan los chunks usando chunker.generar_chunks(list[Clausula]), donde se maneja overlap y metadata para preveer las respuestas a futuro. 

        4. estos chunks se pasan como parametro a embedder.embeber_chunks(list[Chunk]), donde se embeben a la base de datos usando el motor text-embedding-3-small de OpenAI. Este genera un vector de 1536 dimensiones sobre el cual se calculan las similitudes para traer nuevamente las respuestas. Se guardan en la base de datos Neon de PostgreSQL con soporte para busqueda vectorial

        5. Al realizar una pregunta (query), esta se embebe con el mismo procedimiento que lo hicieron los documentos, de modo que conceptos similares quedan ubicados en lugares similares del espacio de 1536 dimensiones (provisto por text-embedding-3-small)

para activar la venv, desde la raiz correr

        venv/Scripts/activate

para cargar todo un directorio para correr

        python run_pipeline.py docs/

para cargar un solo documento para correr

        python run_pipeline.py docs/filename.pdf

para hacer una query correr

        python -m rag.generator "query"


para levantar el frontend: uvicorn api.main:app --reload


No agrego ingestion/ al git: solo mi pc ingiere docs para poder medir consumo de tokens y mi pc se encarga de la carga de pdfs. 