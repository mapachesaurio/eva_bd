# models/viaje_model.py
# Capa MODELO del patrón MVC.
# Aquí va solamente el acceso a la base de datos con PyMongo.
# Este archivo no sabe nada de HTTP ni de las reglas del negocio.

from config.database import get_collection


# ------------------------- CREATE -------------------------

def insertar_viaje(viaje):
    """Inserta un viaje nuevo (ruta + vehiculo + conductor).

    Recibe: viaje (dict) con la estructura de la colección.
    Devuelve: el _id generado por MongoDB como string.
    """
    coleccion = get_collection()
    resultado = coleccion.insert_one(viaje)
    id_generado = str(resultado.inserted_id)
    return id_generado


# ------------------------- READ -------------------------

def listar_viajes(filtro=None):
    """Devuelve una lista de viajes. Se le puede pasar un filtro,
    por ejemplo {"estado_viaje": "EN_TRANSITO"}."""
    if filtro is None:
        filtro = {}

    coleccion = get_collection()
    cursor = coleccion.find(filtro).limit(50)

    viajes = []
    for documento in cursor:
        # el ObjectId no se puede devolver en JSON, lo pasamos a string
        documento["_id"] = str(documento["_id"])
        viajes.append(documento)

    return viajes


def buscar_por_codigo_ruta(codigo_ruta):
    """Busca un viaje por su código de ruta (campo con índice único).
    Devuelve el documento o None si no existe."""
    coleccion = get_collection()
    documento = coleccion.find_one({"codigo_ruta": codigo_ruta})

    if documento is not None:
        documento["_id"] = str(documento["_id"])

    return documento


# ------------------------- UPDATE -------------------------

def agregar_lectura_telemetria(codigo_ruta, lectura):
    """Agrega una lectura de sensores al arreglo telemetria_iot
    usando el operador $push de MongoDB.

    Devuelve la cantidad de documentos modificados (0 si la ruta no existe).
    """
    coleccion = get_collection()
    filtro = {"codigo_ruta": codigo_ruta}
    cambio = {"$push": {"telemetria_iot": lectura}}

    resultado = coleccion.update_one(filtro, cambio)
    return resultado.modified_count


def actualizar_estado_viaje(codigo_ruta, nuevo_estado):
    """Cambia el estado del viaje con $set.
    Devuelve la cantidad de documentos modificados."""
    coleccion = get_collection()
    filtro = {"codigo_ruta": codigo_ruta}
    cambio = {"$set": {"estado_viaje": nuevo_estado}}

    resultado = coleccion.update_one(filtro, cambio)
    return resultado.modified_count


def agregar_capacitacion_conductor(codigo_ruta, capacitacion):
    """Agrega una capacitación al historial del conductor.
    Se usa $push con notación de punto para llegar al subdocumento."""
    coleccion = get_collection()
    filtro = {"codigo_ruta": codigo_ruta}
    cambio = {"$push": {"conductor.capacitaciones": capacitacion}}

    resultado = coleccion.update_one(filtro, cambio)
    return resultado.modified_count


# ------------------------- DELETE -------------------------

def eliminar_viaje(codigo_ruta):
    """Elimina un viaje por su código de ruta.
    Devuelve la cantidad de documentos eliminados (0 o 1)."""
    coleccion = get_collection()
    filtro = {"codigo_ruta": codigo_ruta}

    resultado = coleccion.delete_one(filtro)
    return resultado.deleted_count
