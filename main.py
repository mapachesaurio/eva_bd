# main.py
# Punto de entrada de la aplicación.
# 1. Verifica si la base de datos ya fue poblada. Si no, pregunta si se desea
#    poblarla (respuesta validada: solo "si" o "no").
# 2. Levanta el servidor web con uvicorn sirviendo la API FastAPI.
# Ejecutar con: python main.py  (MongoDB tiene que estar corriendo)

import uvicorn

from config.database import get_collection
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
    """Si la base no fue poblada, ofrece poblarla antes de arrancar el server."""
    if _base_poblada():
        print("[MAIN] La base de datos ya tiene datos, se omite el seed.")
        return
    print("[MAIN] La base de datos está vacía.")
    if _preguntar_si_no("¿Querés poblar la base de datos?"):
        seed.main()
    else:
        print("[MAIN] Se continúa sin poblar la base de datos.")


if __name__ == "__main__":
    _verificar_seed()
    print("[MAIN] Iniciando servidor uvicorn en http://127.0.0.1:8000 ...")
    uvicorn.run("views.viaje_view:app", host="127.0.0.1", port=8000, reload=True)
