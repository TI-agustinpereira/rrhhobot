import os
import logging
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request, Response, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from dotenv import load_dotenv

from api.routes.chats import router as chats_router
from api.auth import verificar_credenciales
from db.connection import verificar_conexion

# Teams es opcional: en el deploy web slim botbuilder no se instala, asi que
# si no esta disponible se omite el adaptador y la app igual sirve la web.
try:
    from botbuilder.core import BotFrameworkAdapter, BotFrameworkAdapterSettings
    from botbuilder.schema import Activity
    from api.bot import HRBot
    TEAMS_DISPONIBLE = True
except ModuleNotFoundError:
    TEAMS_DISPONIBLE = False

"""
main.py

Punto de entrada de la api que registra los routers y el adaptador del bot de Teams

"""

load_dotenv()
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Chatbot RRHH",
    description="RAG sobre contratos laborales y normativas de RRHH y RRLL.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[ "https://*.teams.microsoft.com",
                    # ojo q no anda wildcard * hay q poner todos los dominios a mano 
                    "https://teams.microsoft.com",
                    "https://*.microsoft.com"], 
    # origin restringido a teams o microsoft
    allow_methods=["GET", "POST"],
    # post pues crea mensajes y get envia resultados
    allow_headers=["Authorization", "Content-Type"]
)

# routers REST (protegido con usuario/contraseña)
app.include_router(chats_router, dependencies=[Depends(verificar_credenciales)])

# frontend web estatico (misma URL que la API -> sin problemas de CORS)
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
def index(usuario: str = Depends(verificar_credenciales)):
    """Sirve la pagina web simple del chatbot (requiere login)."""
    return FileResponse(STATIC_DIR / "index.html")


# adaptador Bot Framework (solo si botbuilder esta instalado)
if TEAMS_DISPONIBLE:
    settings = BotFrameworkAdapterSettings(
        app_id=os.getenv("MicrosoftAppId", ""),
        app_password=os.getenv("MicrosoftAppPassword", ""),
    )
    adapter = BotFrameworkAdapter(settings)
    bot = HRBot()

    @app.post("/api/messages")
    async def messages(request: Request):
        """
        endpoint que recibe todos los mensajes de teams
        bot framework autentica la request y la delega al HRBot.
        """
        if "application/json" not in request.headers.get("Content-Type", ""):
            return Response(status_code=415)

        body = await request.json()
        activity = Activity().deserialize(body)
        auth_header = request.headers.get("Authorization", "")

        try:
            await adapter.process_activity(activity, auth_header, bot.on_turn)
        except Exception as e:
            logger.exception("Error procesando request")
            raise HTTPException(status_code=500, detail="Error interno del servidor.")

        return Response(status_code=201)


# health check
@app.get("/health")
def health():
    """verifica que la api este activa y que Neon responde."""
    try:
        verificar_conexion()
        return {"status": "ok", "neon": "conectado"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Neon no disponible: {e}")