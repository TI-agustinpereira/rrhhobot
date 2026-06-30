import os
import secrets
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

"""
auth.py

Autenticacion HTTP Basic para dejar la app privada (un solo usuario).
Las credenciales se leen de las variables de entorno APP_USER y APP_PASSWORD
(se configuran en Render, nunca en el codigo). El navegador muestra un popup
de login al entrar y reusa las credenciales en las llamadas a /chat.
"""

security = HTTPBasic()


def verificar_credenciales(credentials: HTTPBasicCredentials = Depends(security)) -> str:
    """
    Compara las credenciales recibidas contra APP_USER / APP_PASSWORD.
    Usa compare_digest para evitar ataques de timing.
    """
    usuario_esperado = os.getenv("APP_USER", "")
    pass_esperada = os.getenv("APP_PASSWORD", "")

    # fail closed: si no estan configuradas, no se permite el acceso
    if not usuario_esperado or not pass_esperada:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Autenticacion no configurada en el servidor.",
        )

    usuario_ok = secrets.compare_digest(credentials.username, usuario_esperado)
    pass_ok = secrets.compare_digest(credentials.password, pass_esperada)

    if not (usuario_ok and pass_ok):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales invalidas",
            headers={"WWW-Authenticate": "Basic"},
        )

    return credentials.username
