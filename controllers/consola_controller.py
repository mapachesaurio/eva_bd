# controllers/consola_controller.py
# Controlador de la aplicación de consola. Acá está la lógica de qué hace cada
# opción del menú: pide los datos a la vista, aplica las reglas del negocio a
# través de viaje_controller y le pide a la vista que muestre el resultado.
# No lee ni imprime por teclado directamente (de eso se ocupa la vista).

from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

from controllers import viaje_controller
from views import consola_view as vista
import seed


def _listar():
    vista.mostrar_viajes(viaje_controller.obtener_viajes())


def _ver():
    codigo = vista.pedir_texto("Código de ruta")
    viaje = viaje_controller.obtener_viaje(codigo)
    if viaje is None:
        vista.mensaje("No existe ese viaje.")
    else:
        vista.mostrar_viaje(viaje)


def _crear():
    datos = vista.pedir_viaje_nuevo(viaje_controller.ESTADOS_VALIDOS)
    try:
        resultado = viaje_controller.crear_viaje(datos)
        vista.mensaje(f"Viaje creado. id={resultado['id']}  "
                      f"codigo_ruta={resultado['codigo_ruta']}")
    except ValueError as error:
        vista.mensaje(f"No se pudo crear: {error}")


def _telemetria():
    codigo = vista.pedir_texto("Código de ruta")
    lectura = vista.pedir_lectura()
    try:
        viaje = viaje_controller.registrar_telemetria(codigo, lectura)
    except ValueError as error:
        vista.mensaje(f"Lectura rechazada: {error}")
        return
    if viaje is None:
        vista.mensaje("No existe ese viaje.")
    else:
        vista.mensaje(f"Lectura agregada. Total de lecturas: {len(viaje['telemetria_iot'])}")


def _estado():
    codigo = vista.pedir_texto("Código de ruta")
    nuevo = vista.pedir_estado(viaje_controller.ESTADOS_VALIDOS)
    try:
        resultado = viaje_controller.cambiar_estado(codigo, nuevo)
    except ValueError as error:
        vista.mensaje(f"Error: {error}")
        return
    if resultado is None:
        vista.mensaje("No existe ese viaje.")
    else:
        vista.mensaje(f"Estado actualizado a {resultado['estado_viaje']}.")


def _capacitacion():
    codigo = vista.pedir_texto("Código de ruta")
    capacitacion = vista.pedir_capacitacion()
    resultado = viaje_controller.agregar_capacitacion(codigo, capacitacion)
    if resultado is None:
        vista.mensaje("No existe ese viaje.")
    else:
        vista.mensaje("Capacitación agregada al conductor.")


def _eliminar():
    codigo = vista.pedir_texto("Código de ruta")
    if not vista.confirmar(f"¿Eliminar el viaje {codigo}?"):
        vista.mensaje("Cancelado.")
        return
    resultado = viaje_controller.eliminar_viaje(codigo)
    if resultado is None:
        vista.mensaje("No existe ese viaje.")
    else:
        vista.mensaje("Viaje eliminado.")


def _seed():
    seed.main()


ACCIONES = {
    "1": _listar,
    "2": _ver,
    "3": _crear,
    "4": _telemetria,
    "5": _estado,
    "6": _capacitacion,
    "7": _eliminar,
    "8": _seed,
}


def iniciar_app():
    """Bucle principal del menú de consola."""
    vista.mostrar_titulo()
    while True:
        opcion = vista.elegir_opcion()
        if opcion == "0":
            vista.mensaje("Hasta luego.")
            break

        accion = ACCIONES.get(opcion)
        if accion is None:
            vista.mensaje("Opción inválida.")
            continue

        try:
            accion()
        except (ConnectionFailure, ServerSelectionTimeoutError):
            vista.mensaje("ERROR: no se pudo conectar a MongoDB. ¿Está corriendo el servicio?")
