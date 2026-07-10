# main.py
# Punto de entrada de la aplicación de consola.
# No tiene lógica: solo arranca el controlador. El flujo del menú está en
# controllers/consola_controller.py y la interfaz en views/consola_view.py.
# Ejecutar con: python main.py  (MongoDB tiene que estar corriendo)

from controllers.consola_controller import iniciar_app


if __name__ == "__main__":
    iniciar_app()
