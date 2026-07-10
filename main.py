# main.py
# Punto de entrada de la aplicación.
# No tiene lógica: solo arranca el controlador de sistema, que se encarga del
# seed opcional, del servidor web (uvicorn) y del menú de consola.
# Ejecutar con: python main.py  (MongoDB tiene que estar corriendo)

from controllers.app_controller import iniciar_sistema


if __name__ == "__main__":
    iniciar_sistema()
