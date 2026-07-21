import os
from botbuilder.core import ActivityHandler, TurnContext, MessageFactory
from botbuilder.schema import Activity
from rag.generator import responder

"""
bot.py

Adaptador del bot de Microsoft Teams.
Recibe mensajes del Bot Framework, llama al RAG y devuelve la respuesta.

Requiere en .env microsoft app id y password
"""


class HRBot(ActivityHandler):
    """
    bot de RRHH para Microsoft Teams.

    cada mensaje es independiente (sin historial): recibe la pregunta,
    consulta el RAG y responde. No expone nombres de documentos ni
    permite que el usuario filtre por documento.
    """

    async def on_message_activity(self, turn_context: TurnContext):
        pregunta = turn_context.activity.text

        if not pregunta or not pregunta.strip():
            await turn_context.send_activity(
                MessageFactory.text("Por favor escribí tu pregunta.")
            )
            return

        # indicador de escritura mientras el RAG procesa
        await turn_context.send_activity(Activity(type="typing"))

        try:
            resultado = responder(query=pregunta.strip())
        except Exception as e:
            await turn_context.send_activity(
                MessageFactory.text(
                    "Ocurrió un error al procesar tu consulta. Intentá de nuevo en unos momentos."
                )
            )
            return

        respuesta_texto = resultado["respuesta"]
        chunks = resultado["chunks"]

        # armar fuentes citando el documento de origen
        if chunks:
            fuentes_lines = []
            seen = set()
            for c in chunks:
                documento = c.metadata.get("documento", "?")
                pagina = c.metadata.get("pagina", 0)
                key = (documento, pagina)
                if key not in seen:
                    seen.add(key)
                    label = documento
                    if pagina:
                        label += f" (p. {pagina})"
                    fuentes_lines.append(f"• {label}")

            fuentes_texto = "\n".join(fuentes_lines)
            mensaje_final = f"{respuesta_texto}\n\n**Fuentes consultadas:**\n{fuentes_texto}"
        else:
            mensaje_final = respuesta_texto

        await turn_context.send_activity(MessageFactory.text(mensaje_final))