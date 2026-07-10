# controllers/app_controller.py
# Controlador de arranque de la aplicación. Orquesta el inicio del sistema:
#   1. Verifica si la base de datos fue poblada y, si no, ofrece poblarla.
#   2. Levanta el servidor web (uvicorn) en un hilo de fondo.
#   3. Corre el menú de consola en el hilo principal, en paralelo al servidor.
# main.py solo llama a iniciar_sistema(): toda la lógica vive acá.

import threading

import uvicorn

from config.database import get_collection
from config.esquema import inicializar_esquema
from controllers.consola_controller import iniciar_app
from views.viaje_view import app
import seed


def _base_poblada():
    """Devuelve True si ya hay al menos un viaje cargado en la colección."""
    return get_collection().count_documents({}, limit=1) > 0


def _preguntar_si_no(pregunta):
    """Pide una respuesta si/no y no avanza hasta recibir una válida."""
    while True:
        respuesta = input(f"{pregunta} (si/no): ").strip().lower()
        if respuesta in ("si", "no"):
            return respuesta == "si"
        print("Respuesta inválida. Escribí 'si' o 'no'.")


def _verificar_seed():
    """Si la base no fue poblada, ofrece poblarla antes de arrancar."""
    if _base_poblada():
        print("[MAIN] La base de datos ya tiene datos, se omite el seed.")
        return
    print("[MAIN] La base de datos está vacía.")
    if _preguntar_si_no("¿Querés poblar la base de datos?"):
        seed.main()
    else:
        print("[MAIN] Se continúa sin poblar la base de datos.")


def _iniciar_servidor():
    """Arranca uvicorn. Sin reload: corre en un hilo secundario, donde el
    recargador de uvicorn no puede manejar señales del sistema."""
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="warning")


def iniciar_sistema():
    """Punto de arranque: esquema, seed opcional, servidor web y menú en paralelo."""
    # Primero el esquema: la colección/validador/índices deben existir antes de
    # que el seed inserte, para que el validador aplique a los datos de ejemplo.
    inicializar_esquema()
    _verificar_seed()

    # El servidor corre en un hilo daemon: se cierra solo cuando el menú
    # (hilo principal) termina, así no queda un proceso colgado.
    hilo_servidor = threading.Thread(target=_iniciar_servidor, daemon=True)
    hilo_servidor.start()
    print("[MAIN] Servidor uvicorn corriendo en http://127.0.0.1:8000/docs")

    # El menú de consola corre en primer plano, en paralelo al servidor.
    iniciar_app()
