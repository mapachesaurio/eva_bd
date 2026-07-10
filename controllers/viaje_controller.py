# controllers/viaje_controller.py
# Capa CONTROLADOR del patrón MVC.
# Aquí van las reglas del negocio: validaciones y decisiones antes de
# guardar en la base de datos. No arma respuestas HTTP (eso lo hace la
# vista) y no usa PyMongo directo (eso lo hace el modelo).

from datetime import datetime, timezone

from pymongo.errors import DuplicateKeyError, WriteError

from models import viaje_model

# Estados que permite el negocio para un viaje
ESTADOS_VALIDOS = ["PROGRAMADO", "EN_TRANSITO", "FINALIZADO", "CANCELADO"]


def crear_viaje(datos):
    """Da de alta un viaje nuevo con su vehículo y conductor.

    Valida los datos básicos y luego llama al modelo.
    Si algo está mal, lanza ValueError con el motivo.
    """
    estado = datos["estado_viaje"]
    if estado not in ESTADOS_VALIDOS:
        raise ValueError(f"El estado '{estado}' no es válido. Debe ser uno de: {ESTADOS_VALIDOS}")

    # el VIN de un vehículo siempre tiene 17 caracteres
    vin = datos["vehiculo"]["vin"]
    if len(vin) != 17:
        raise ValueError(f"El VIN '{vin}' no es válido: debe tener 17 caracteres")

    try:
        id_nuevo = viaje_model.insertar_viaje(datos)
    except DuplicateKeyError:
        # el índice único de codigo_ruta no deja insertar rutas repetidas
        codigo = datos["codigo_ruta"]
        raise ValueError(f"Ya existe un viaje con el código {codigo}")
    except WriteError:
        # el validador de esquema de MongoDB rechazó el documento
        raise ValueError("El documento no cumple con el esquema de la colección")

    respuesta = {"id": id_nuevo, "codigo_ruta": datos["codigo_ruta"]}
    return respuesta


def obtener_viajes(estado=None):
    """Devuelve la lista de viajes, con filtro opcional por estado."""
    if estado is not None:
        filtro = {"estado_viaje": estado}
        return viaje_model.listar_viajes(filtro)

    return viaje_model.listar_viajes()


def obtener_viaje(codigo_ruta):
    """Busca un viaje puntual. Devuelve None si no existe
    (la vista se encarga de responder el 404)."""
    viaje = viaje_model.buscar_por_codigo_ruta(codigo_ruta)
    return viaje


def registrar_telemetria(codigo_ruta, lectura):
    """Valida una lectura de sensores y la agrega al viaje.

    Revisamos que los valores tengan sentido físico antes de guardarlos,
    porque un sensor con fallas puede mandar cualquier cosa.
    La fecha la ponemos nosotros en el servidor (UTC) para que todas las
    lecturas queden ordenadas con el mismo reloj.
    """
    velocidad = lectura["velocidad_kmh"]
    if velocidad < 0 or velocidad > 200:
        raise ValueError(f"Velocidad fuera de rango: {velocidad} km/h")

    temperatura = lectura["temperatura_motor_c"]
    if temperatura < -40 or temperatura > 150:
        raise ValueError(f"Temperatura fuera de rango: {temperatura} °C")

    combustible = lectura["nivel_combustible_porcentaje"]
    if combustible < 0 or combustible > 100:
        raise ValueError(f"El nivel de combustible debe estar entre 0 y 100 (llegó {combustible})")

    # la fecha se genera en el servidor, no en el sensor
    lectura["timestamp"] = datetime.now(timezone.utc)

    modificados = viaje_model.agregar_lectura_telemetria(codigo_ruta, lectura)
    if modificados == 0:
        # la ruta no existe
        return None

    viaje_actualizado = viaje_model.buscar_por_codigo_ruta(codigo_ruta)
    return viaje_actualizado


def cambiar_estado(codigo_ruta, nuevo_estado):
    """Cambia el estado de un viaje validando que sea un estado permitido."""
    if nuevo_estado not in ESTADOS_VALIDOS:
        raise ValueError(f"El estado '{nuevo_estado}' no es válido. Debe ser uno de: {ESTADOS_VALIDOS}")

    modificados = viaje_model.actualizar_estado_viaje(codigo_ruta, nuevo_estado)
    if modificados == 0:
        return None

    respuesta = {"codigo_ruta": codigo_ruta, "estado_viaje": nuevo_estado}
    return respuesta


def agregar_capacitacion(codigo_ruta, capacitacion):
    """Agrega una certificación al historial del conductor del viaje."""
    modificados = viaje_model.agregar_capacitacion_conductor(codigo_ruta, capacitacion)
    if modificados == 0:
        return None

    respuesta = {"codigo_ruta": codigo_ruta, "capacitacion_agregada": capacitacion}
    return respuesta


def eliminar_viaje(codigo_ruta):
    """Elimina un viaje. Devuelve None si no existía."""
    eliminados = viaje_model.eliminar_viaje(codigo_ruta)
    if eliminados == 0:
        return None

    respuesta = {"codigo_ruta": codigo_ruta, "eliminado": True}
    return respuesta
