# LogiTrack_Global - Código fuente

Volcado completo del código del proyecto, ordenado por carpeta y archivo.

## Estructura

```
logitrack_mvc/
├── config/
│   ├── __init__.py
│   └── database.py
├── models/
│   ├── __init__.py
│   └── viaje_model.py
├── controllers/
│   ├── __init__.py
│   ├── viaje_controller.py
│   └── consola_controller.py
├── views/
│   ├── __init__.py
│   ├── viaje_view.py
│   └── consola_view.py
├── scripts/
│   └── crear_esquema.js
├── main.py
├── seed.py
├── test_mvp.py
├── requirements.txt
├── .env.example
└── .gitignore
```

Los archivos `__init__.py` de `config/`, `models/`, `controllers/` y `views/` están vacíos:
solo marcan cada carpeta como paquete de Python.

---

## config/

### config/database.py

```python
# config/database.py
# Conexión a MongoDB para el proyecto LogiTrack_Global.
# Las credenciales se leen desde el archivo .env para no dejarlas
# escritas en el código (el .env no se sube al repositorio).

import os

from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, OperationFailure

# Carga las variables del archivo .env
load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB = os.getenv("MONGO_DB", "logitrack_global")
MONGO_COLL = os.getenv("MONGO_COLL", "viajes_monitoreo")

# Usamos un solo cliente para toda la aplicación.
# PyMongo maneja internamente un pool de conexiones, por eso no hay
# que crear un cliente nuevo en cada consulta.
cliente = None


def get_collection():
    """Devuelve la colección viajes_monitoreo para usarla en los modelos.
    La primera vez que se llama, abre la conexión y hace un ping para
    comprobar que la base de datos responde."""
    global cliente
    if cliente is None:
        try:
            cliente = MongoClient(
                MONGO_URI,
                maxPoolSize=50,                 # límite de conexiones simultáneas
                serverSelectionTimeoutMS=5000,  # si no responde en 5 seg, da error
            )
            cliente.admin.command("ping")
        except ConnectionFailure:
            print("ERROR: no se pudo conectar a MongoDB. ¿Está corriendo el servicio?")
            raise
        except OperationFailure:
            print("ERROR: usuario o contraseña incorrectos (revisar archivo .env)")
            raise
    return cliente[MONGO_DB][MONGO_COLL]
```

---

## models/

### models/viaje_model.py

```python
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
```

---

## controllers/

### controllers/viaje_controller.py

```python
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
```

### controllers/consola_controller.py

```python
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
```

---

## views/

### views/viaje_view.py

```python
# views/viaje_view.py
# Capa VISTA del patrón MVC.
# Define los endpoints de la API con FastAPI. Recibe las peticiones,
# valida el formato con Pydantic, llama al controlador y devuelve la
# respuesta HTTP. No toca la base de datos directamente.
#
# Para correr el servidor:  uvicorn views.viaje_view:app --reload
# Documentación automática: http://127.0.0.1:8000/docs

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from controllers import viaje_controller

app = FastAPI(
    title="LogiTrack_Global - MVP de Monitoreo de Flotas",
    description="API para gestionar viajes, vehículos, conductores y telemetría IoT",
    version="1.0",
)


# --------- Esquemas Pydantic (formato que espera cada endpoint) ---------

class Licencia(BaseModel):
    tipo: str
    fecha_vencimiento: str


class Capacitacion(BaseModel):
    centro_educativo: str
    ano: int
    certificacion_obtenida: str


class Conductor(BaseModel):
    rut_id: str
    nombre: str
    primer_apellido: str
    nacionalidad: str
    licencia: Licencia
    capacitaciones: list[Capacitacion] = []
    observaciones_desempeño: str = ""


class Vehiculo(BaseModel):
    vin: str
    patente: str
    marca: str
    modelo: str
    ano_fabricacion: int
    tipo_combustible: str
    capacidad_carga_max_Kg: int
    observaciones_mecanicas: str = ""


class LecturaIoT(BaseModel):
    latitud: float
    longitud: float
    velocidad_kmh: float
    temperatura_motor_c: float
    nivel_combustible_porcentaje: float
    alerta_sistema: str | None = None


class ViajeNuevo(BaseModel):
    codigo_ruta: str
    origen: str
    destino: str
    tiempo_estimado_dias: float
    estado_viaje: str = "PROGRAMADO"
    centro_contacto_despacho: dict
    vehiculo: Vehiculo
    conductor: Conductor


class CambioEstado(BaseModel):
    estado_viaje: str


# ------------------------- Endpoints CRUD -------------------------

@app.post("/viajes", status_code=201)
def crear_viaje(viaje: ViajeNuevo):
    """CREATE: registra un viaje nuevo con vehículo y conductor."""
    datos = viaje.model_dump()
    datos["telemetria_iot"] = []  # el arreglo de sensores parte vacío
    try:
        return viaje_controller.crear_viaje(datos)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))


@app.get("/viajes")
def listar_viajes(estado: str | None = None):
    """READ: lista los viajes. Se puede filtrar con ?estado=EN_TRANSITO"""
    return viaje_controller.obtener_viajes(estado)


@app.get("/viajes/{codigo_ruta}")
def obtener_viaje(codigo_ruta: str):
    """READ: devuelve un viaje puntual por su código."""
    viaje = viaje_controller.obtener_viaje(codigo_ruta)
    if viaje is None:
        raise HTTPException(status_code=404, detail=f"No existe el viaje {codigo_ruta}")
    return viaje


@app.post("/viajes/{codigo_ruta}/telemetria")
def registrar_telemetria(codigo_ruta: str, lectura: LecturaIoT):
    """UPDATE: agrega una lectura IoT al arreglo del viaje (usa $push)."""
    datos = lectura.model_dump()

    # armamos el punto GeoJSON con la latitud y longitud recibidas
    latitud = datos.pop("latitud")
    longitud = datos.pop("longitud")
    datos["ubicacion"] = {
        "tipo": "Point",
        "coordenadas": [longitud, latitud],
    }
    try:
        viaje = viaje_controller.registrar_telemetria(codigo_ruta, datos)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))
    if viaje is None:
        raise HTTPException(status_code=404, detail=f"No existe el viaje {codigo_ruta}")
    return viaje


@app.patch("/viajes/{codigo_ruta}/estado")
def cambiar_estado(codigo_ruta: str, cambio: CambioEstado):
    """UPDATE: cambia el estado del viaje (PROGRAMADO, EN_TRANSITO, etc.)."""
    try:
        resultado = viaje_controller.cambiar_estado(codigo_ruta, cambio.estado_viaje)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))
    if resultado is None:
        raise HTTPException(status_code=404, detail=f"No existe el viaje {codigo_ruta}")
    return resultado


@app.post("/viajes/{codigo_ruta}/conductor/capacitaciones")
def agregar_capacitacion(codigo_ruta: str, capacitacion: Capacitacion):
    """UPDATE: agrega una capacitación al conductor del viaje."""
    datos_capacitacion = capacitacion.model_dump()
    resultado = viaje_controller.agregar_capacitacion(codigo_ruta, datos_capacitacion)
    if resultado is None:
        raise HTTPException(status_code=404, detail=f"No existe el viaje {codigo_ruta}")
    return resultado


@app.delete("/viajes/{codigo_ruta}")
def eliminar_viaje(codigo_ruta: str):
    """DELETE: elimina un viaje completo."""
    resultado = viaje_controller.eliminar_viaje(codigo_ruta)
    if resultado is None:
        raise HTTPException(status_code=404, detail=f"No existe el viaje {codigo_ruta}")
    return resultado
```

### views/consola_view.py

```python
# views/consola_view.py
# Vista de consola. Solo se encarga de mostrar información y pedir datos por
# teclado. No tiene reglas de negocio ni acceso a la base: de eso se ocupa el
# controlador. El controlador la llama para leer y para mostrar.

MENU = """
Menú:
  1. Listar viajes
  2. Ver un viaje
  3. Crear viaje
  4. Registrar telemetría
  5. Cambiar estado
  6. Agregar capacitación al conductor
  7. Eliminar viaje
  8. Cargar datos de ejemplo (seed)
  0. Salir"""


def mostrar_titulo():
    print("=== LogiTrack_Global - Consola de gestión de viajes ===")


def elegir_opcion():
    print(MENU)
    return input("Elegí una opción: ").strip()


def mensaje(texto):
    print(texto)


# ------------------------- Lectura de datos -------------------------

def pedir_texto(etiqueta, obligatorio=True):
    while True:
        valor = input(f"{etiqueta}: ").strip()
        if valor or not obligatorio:
            return valor
        print("  * Este dato es obligatorio.")


def pedir_entero(etiqueta):
    while True:
        try:
            return int(input(f"{etiqueta}: ").strip())
        except ValueError:
            print("  * Ingresá un número entero.")


def pedir_decimal(etiqueta):
    while True:
        try:
            return float(input(f"{etiqueta}: ").strip())
        except ValueError:
            print("  * Ingresá un número (se admiten decimales).")


def pedir_estado(estados):
    while True:
        valor = input(f"Estado ({', '.join(estados)}): ").strip().upper()
        if valor in estados:
            return valor
        print("  * Estado inválido.")


def confirmar(pregunta):
    return input(f"{pregunta} (s/n): ").strip().lower() == "s"


# ------------------------- Formularios -------------------------

def pedir_viaje_nuevo(estados):
    """Arma el diccionario de un viaje nuevo con los datos que ingresa el usuario."""
    return {
        "codigo_ruta": pedir_texto("Código de ruta"),
        "origen": pedir_texto("Origen"),
        "destino": pedir_texto("Destino"),
        "tiempo_estimado_dias": pedir_decimal("Tiempo estimado (días)"),
        "estado_viaje": pedir_estado(estados),
        "centro_contacto_despacho": {
            "nombre_contacto": pedir_texto("Despacho - nombre de contacto"),
            "telefono": pedir_texto("Despacho - teléfono"),
            "ciudad": pedir_texto("Despacho - ciudad"),
        },
        "vehiculo": {
            "vin": pedir_texto("Vehículo - VIN (17 caracteres)"),
            "patente": pedir_texto("Vehículo - patente"),
            "marca": pedir_texto("Vehículo - marca"),
            "modelo": pedir_texto("Vehículo - modelo"),
            "ano_fabricacion": pedir_entero("Vehículo - año de fabricación"),
            "tipo_combustible": pedir_texto("Vehículo - tipo de combustible"),
            "capacidad_carga_max_Kg": pedir_entero("Vehículo - capacidad de carga (Kg)"),
        },
        "conductor": {
            "rut_id": pedir_texto("Conductor - RUT / ID"),
            "nombre": pedir_texto("Conductor - nombre"),
            "primer_apellido": pedir_texto("Conductor - primer apellido"),
            "nacionalidad": pedir_texto("Conductor - nacionalidad"),
            "licencia": {
                "tipo": pedir_texto("Licencia - tipo"),
                "fecha_vencimiento": pedir_texto("Licencia - vencimiento (AAAA-MM-DD)"),
            },
            "capacitaciones": [],
        },
        "telemetria_iot": [],
    }


def pedir_lectura():
    """Arma una lectura de telemetría. La ubicación se guarda como punto GeoJSON."""
    latitud = pedir_decimal("Latitud")
    longitud = pedir_decimal("Longitud")
    return {
        "velocidad_kmh": pedir_decimal("Velocidad (km/h)"),
        "temperatura_motor_c": pedir_decimal("Temperatura motor (°C)"),
        "nivel_combustible_porcentaje": pedir_decimal("Nivel de combustible (%)"),
        "alerta_sistema": pedir_texto("Alerta (Enter si no hay)", obligatorio=False) or None,
        "ubicacion": {"tipo": "Point", "coordenadas": [longitud, latitud]},
    }


def pedir_capacitacion():
    return {
        "centro_educativo": pedir_texto("Centro educativo"),
        "ano": pedir_entero("Año"),
        "certificacion_obtenida": pedir_texto("Certificación obtenida"),
    }


# ------------------------- Salida de datos -------------------------

def mostrar_viajes(viajes):
    if not viajes:
        print("No hay viajes cargados.")
        return
    print(f"\n{len(viajes)} viaje(s):")
    for v in viajes:
        cond = v.get("conductor", {})
        conductor = f"{cond.get('nombre', '?')} {cond.get('primer_apellido', '')}".strip()
        print(f"  - {v.get('codigo_ruta', '(sin código)')}: "
              f"{v.get('origen', '?')} -> {v.get('destino', '?')} "
              f"[{v.get('estado_viaje', '?')}]  conductor: {conductor}")


def mostrar_viaje(v):
    """Muestra un viaje como una ficha ordenada en la terminal."""
    titulo = f"VIAJE {v.get('codigo_ruta', '(sin código)')}"
    print()
    print(titulo)
    print("-" * len(titulo))
    print(f"Ruta:            {v.get('origen', '?')} -> {v.get('destino', '?')}")
    print(f"Estado:          {v.get('estado_viaje', '?')}")
    print(f"Tiempo estimado: {v.get('tiempo_estimado_dias', '?')} días")

    despacho = v.get("centro_contacto_despacho", {})
    if despacho:
        print("\nDespacho")
        print(f"  Contacto: {despacho.get('nombre_contacto', '-')}")
        print(f"  Teléfono: {despacho.get('telefono', '-')}")
        print(f"  Ciudad:   {despacho.get('ciudad', '-')}")
        if despacho.get("observaciones_logistica"):
            print(f"  Notas:    {despacho['observaciones_logistica']}")

    vehiculo = v.get("vehiculo", {})
    if vehiculo:
        modelo = f"{vehiculo.get('marca', '')} {vehiculo.get('modelo', '')}".strip()
        if vehiculo.get("ano_fabricacion"):
            modelo += f" ({vehiculo['ano_fabricacion']})"
        print("\nVehículo")
        print(f"  Marca/Modelo: {modelo or '-'}")
        print(f"  Patente:      {vehiculo.get('patente', '-')}")
        print(f"  VIN:          {vehiculo.get('vin', '-')}")
        print(f"  Combustible:  {vehiculo.get('tipo_combustible', '-')}")
        print(f"  Capacidad:    {vehiculo.get('capacidad_carga_max_Kg', '-')} Kg")

    conductor = v.get("conductor", {})
    if conductor:
        print("\nConductor")
        nombre = f"{conductor.get('nombre', '')} {conductor.get('primer_apellido', '')}".strip()
        print(f"  Nombre:       {nombre or '-'}")
        print(f"  Nacionalidad: {conductor.get('nacionalidad', '-')}")
        licencia = conductor.get("licencia", {})
        if licencia:
            print(f"  Licencia:     {licencia.get('tipo', '-')} "
                  f"(vence {licencia.get('fecha_vencimiento', '-')})")
        capacitaciones = conductor.get("capacitaciones", [])
        if capacitaciones:
            print("  Capacitaciones:")
            for cap in capacitaciones:
                print(f"    - {cap.get('ano', '?')}  {cap.get('certificacion_obtenida', '-')} "
                      f"({cap.get('centro_educativo', '-')})")

    lecturas = v.get("telemetria_iot", [])
    print(f"\nTelemetría ({len(lecturas)} lectura(s))")
    for lectura in lecturas:
        momento = str(lectura.get("timestamp", ""))[:16]
        alerta = lectura.get("alerta_sistema") or "sin alerta"
        print(f"  [{momento}] "
              f"vel {lectura.get('velocidad_kmh', '?')} km/h | "
              f"motor {lectura.get('temperatura_motor_c', '?')} °C | "
              f"comb {lectura.get('nivel_combustible_porcentaje', '?')} % | {alerta}")
    print()
```

---

## scripts/

### scripts/crear_esquema.js

```javascript
// scripts/crear_esquema.js
// -------------------------
// Script de inicialización del DBMS (ejecutar con mongosh o MongoDB Compass).
// Crea la base de datos, la colección con validador $jsonSchema ESTRICTO
// (requisitos G.7 y G.8) y los índices de rendimiento para alta demanda.
//
// Uso:  mongosh "mongodb://localhost:27017" scripts/crear_esquema.js

db = db.getSiblingDB("logitrack_global");

db.createCollection("viajes_monitoreo", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["codigo_ruta", "origen", "destino", "estado_viaje", "vehiculo", "conductor"],
      properties: {
        codigo_ruta: {
          bsonType: "string",
          description: "String único identificador de la ruta logística. Obligatorio."
        },
        origen: { bsonType: "string" },
        destino: { bsonType: "string" },
        tiempo_estimado_dias: { bsonType: ["double", "int"] },
        estado_viaje: {
          enum: ["PROGRAMADO", "EN_TRANSITO", "FINALIZADO", "CANCELADO"],
          description: "Restringido a los estados operativos de la última milla."
        },
        centro_contacto_despacho: {
          bsonType: "object",
          properties: {
            nombre_contacto: { bsonType: "string" },
            telefono: { bsonType: "string" },
            ciudad: { bsonType: "string" },
            observaciones_logistica: { bsonType: "string" }
          }
        },
        vehiculo: {
          bsonType: "object",
          required: ["vin", "patente", "marca", "modelo", "capacidad_carga_max_Kg"],
          properties: {
            vin: { bsonType: "string", minLength: 17, maxLength: 17 },
            patente: { bsonType: "string" },
            marca: { bsonType: "string" },
            modelo: { bsonType: "string" },
            ano_fabricacion: { bsonType: "int" },
            tipo_combustible: { bsonType: "string" },
            capacidad_carga_max_Kg: { bsonType: "int", minimum: 1 },
            observaciones_mecanicas: { bsonType: "string" }
          }
        },
        conductor: {
          bsonType: "object",
          required: ["rut_id", "nombre", "primer_apellido", "nacionalidad"],
          properties: {
            rut_id: { bsonType: "string" },
            nombre: { bsonType: "string" },
            primer_apellido: { bsonType: "string" },
            nacionalidad: { bsonType: "string" },
            licencia: {
              bsonType: "object",
              properties: {
                tipo: { bsonType: "string" },
                fecha_vencimiento: { bsonType: ["date", "string"] }
              }
            },
            capacitaciones: {
              bsonType: "array",
              items: {
                bsonType: "object",
                properties: {
                  centro_educativo: { bsonType: "string" },
                  ano: { bsonType: "int" },
                  certificacion_obtenida: { bsonType: "string" }
                }
              }
            },
            observaciones_desempeño: { bsonType: "string" },
            jerarquia: {
              bsonType: "object",
              properties: {
                supervisor_id: { bsonType: ["objectId", "string"] },
                nombres_conductores_supervisados: {
                  bsonType: "array",
                  items: { bsonType: "string" }
                }
              }
            }
          }
        },
        telemetria_iot: {
          bsonType: "array",
          items: {
            bsonType: "object",
            required: ["timestamp", "velocidad_kmh", "temperatura_motor_c", "nivel_combustible_porcentaje"],
            properties: {
              timestamp: { bsonType: "date" },
              ubicacion: {
                bsonType: "object",
                properties: {
                  tipo: { enum: ["Point"] },
                  coordenadas: { bsonType: "array", items: { bsonType: "double" } }
                }
              },
              velocidad_kmh: { bsonType: ["double", "int"] },
              temperatura_motor_c: { bsonType: ["double", "int"] },
              nivel_combustible_porcentaje: { bsonType: ["double", "int"] },
              alerta_sistema: { bsonType: ["string", "null"] }
            }
          }
        }
      }
    }
  },
  validationLevel: "strict",   // valida TODA inserción y actualización
  validationAction: "error"    // rechaza documentos inválidos (no solo advierte)
});

// Índices estratégicos para la carga proyectada de 20.000 req/min (G.7)
db.viajes_monitoreo.createIndex({ "codigo_ruta": 1 }, { unique: true });
db.viajes_monitoreo.createIndex({ "vehiculo.vin": 1 });
db.viajes_monitoreo.createIndex({ "conductor.rut_id": 1 });
db.viajes_monitoreo.createIndex({ "estado_viaje": 1 });
db.viajes_monitoreo.createIndex({ "telemetria_iot.timestamp": -1 });

print("Colección viajes_monitoreo creada con validador estricto e índices.");
```

---

## Raíz del proyecto

### main.py

```python
# main.py
# Punto de entrada de la aplicación de consola.
# No tiene lógica: solo arranca el controlador. El flujo del menú está en
# controllers/consola_controller.py y la interfaz en views/consola_view.py.
# Ejecutar con: python main.py  (MongoDB tiene que estar corriendo)

from controllers.consola_controller import iniciar_app


if __name__ == "__main__":
    iniciar_app()
```

### seed.py

```python
# seed.py
# Carga 3 viajes de ejemplo (con vehículo, conductor y lecturas IoT).
# Ejecutar con: python seed.py

from datetime import datetime, timezone

from config.database import get_collection


def construir_datos_semilla():
    """Devuelve la lista de viajes a insertar."""
    ahora = datetime.now(timezone.utc)
    return [
        {
            "codigo_ruta": "RT-GLOBAL-2026-99A",
            "origen": "Santiago, Chile",
            "destino": "Mendoza, Argentina",
            "tiempo_estimado_dias": 1.5,
            "estado_viaje": "EN_TRANSITO",
            "centro_contacto_despacho": {
                "nombre_contacto": "Carlos Mendoza",
                "telefono": "+56987654321",
                "ciudad": "Santiago",
                "observaciones_logistica": (
                    "Ruta crítica de cordillera, paso Los Libertadores. "
                    "Monitorear alertas de congelamiento de frenos."
                ),
            },
            "vehiculo": {
                "vin": "1HGCR2F8XHA000000",
                "patente": "ABCD-12",
                "marca": "Volvo",
                "modelo": "FH16 Globetrotter",
                "ano_fabricacion": 2024,
                "tipo_combustible": "Diesel / Híbrido",
                "capacidad_carga_max_Kg": 45000,
                "observaciones_mecanicas": (
                    "Cambio de pastillas de freno delanteras realizado en taller central."
                ),
            },
            "conductor": {
                "rut_id": "12345678-9",
                "nombre": "Juan",
                "primer_apellido": "Pérez",
                "nacionalidad": "Chilena",
                "licencia": {"tipo": "A5", "fecha_vencimiento": "2029-08-20"},
                "capacitaciones": [
                    {
                        "centro_educativo": "Instituto Superior de Transportes",
                        "ano": 2022,
                        "certificacion_obtenida": "Conducción Eficiente y Segura de Carga Pesada",
                    },
                    {
                        "centro_educativo": "LogiTrack Academy",
                        "ano": 2024,
                        "certificacion_obtenida": "Operación de Sensores IoT y Telemetría Avanzada",
                    },
                ],
                "observaciones_desempeño": "Conductor destacado. Excelente consumo de combustible.",
                "jerarquia": {
                    "supervisor_id": "JF-REGIONAL-CONO-SUR-01",
                    "nombres_conductores_supervisados": ["Diego Muñoz", "Cristian Soto"],
                },
            },
            "telemetria_iot": [
                {
                    "timestamp": ahora,
                    "ubicacion": {"tipo": "Point", "coordenadas": [-70.6483, -33.4569]},
                    "velocidad_kmh": 85.5,
                    "temperatura_motor_c": 92.0,
                    "nivel_combustible_porcentaje": 78.2,
                    "alerta_sistema": None,
                },
                {
                    "timestamp": ahora,
                    "ubicacion": {"tipo": "Point", "coordenadas": [-70.6520, -33.4610]},
                    "velocidad_kmh": 0.0,
                    "temperatura_motor_c": 94.5,
                    "nivel_combustible_porcentaje": 78.1,
                    "alerta_sistema": "FRENADO_BRUSCO",
                },
            ],
        },
        {
            "codigo_ruta": "RT-GLOBAL-2026-77B",
            "origen": "Valparaíso, Chile",
            "destino": "Antofagasta, Chile",
            "tiempo_estimado_dias": 2.0,
            "estado_viaje": "PROGRAMADO",
            "centro_contacto_despacho": {
                "nombre_contacto": "María Riquelme",
                "telefono": "+56911223344",
                "ciudad": "Valparaíso",
                "observaciones_logistica": "Carga refrigerada. Verificar cadena de frío.",
            },
            "vehiculo": {
                "vin": "WDB9634031L000001",
                "patente": "EFGH-34",
                "marca": "Mercedes-Benz",
                "modelo": "Actros 2651",
                "ano_fabricacion": 2023,
                "tipo_combustible": "Diesel",
                "capacidad_carga_max_Kg": 40000,
                "observaciones_mecanicas": "Mantención de 60.000 km al día.",
            },
            "conductor": {
                "rut_id": "17654321-0",
                "nombre": "Diego",
                "primer_apellido": "Muñoz",
                "nacionalidad": "Chilena",
                "licencia": {"tipo": "A5", "fecha_vencimiento": "2027-03-15"},
                "capacitaciones": [
                    {
                        "centro_educativo": "LogiTrack Academy",
                        "ano": 2025,
                        "certificacion_obtenida": "Inducción de Flota y Seguridad Vial",
                    }
                ],
                "observaciones_desempeño": "Conductor novato bajo tutoría de Juan Pérez.",
                "jerarquia": {
                    "supervisor_id": "12345678-9",
                    "nombres_conductores_supervisados": [],
                },
            },
            "telemetria_iot": [],
        },
        {
            "codigo_ruta": "RT-GLOBAL-2026-55C",
            "origen": "Lima, Perú",
            "destino": "Quito, Ecuador",
            "tiempo_estimado_dias": 4.5,
            "estado_viaje": "FINALIZADO",
            "centro_contacto_despacho": {
                "nombre_contacto": "Andrés Salas",
                "telefono": "+51987112233",
                "ciudad": "Lima",
                "observaciones_logistica": "Ruta internacional con doble control aduanero.",
            },
            "vehiculo": {
                "vin": "YV2RT40A8KB000002",
                "patente": "IJKL-56",
                "marca": "Scania",
                "modelo": "R500",
                "ano_fabricacion": 2022,
                "tipo_combustible": "Diesel",
                "capacidad_carga_max_Kg": 38000,
                "observaciones_mecanicas": "Sin incidencias.",
            },
            "conductor": {
                "rut_id": "PA-8877665",
                "nombre": "Cristian",
                "primer_apellido": "Soto",
                "nacionalidad": "Peruana",
                "licencia": {"tipo": "A4", "fecha_vencimiento": "2028-11-02"},
                "capacitaciones": [],
                "observaciones_desempeño": "Cumple estándares. Supervisado por Juan Pérez.",
                "jerarquia": {
                    "supervisor_id": "12345678-9",
                    "nombres_conductores_supervisados": [],
                },
            },
            "telemetria_iot": [
                {
                    "timestamp": ahora,
                    "ubicacion": {"tipo": "Point", "coordenadas": [-77.0428, -12.0464]},
                    "velocidad_kmh": 62.0,
                    "temperatura_motor_c": 88.7,
                    "nivel_combustible_porcentaje": 45.0,
                    "alerta_sistema": None,
                }
            ],
        },
    ]


def main():
    """Inserta los viajes. Los que ya existen (mismo codigo_ruta) se omiten."""
    coleccion = get_collection()
    insertados = 0
    for doc in construir_datos_semilla():
        if coleccion.count_documents({"codigo_ruta": doc["codigo_ruta"]}, limit=1) == 0:
            coleccion.insert_one(doc)
            insertados += 1
            print(f"[SEED] Insertado viaje {doc['codigo_ruta']}")
        else:
            print(f"[SEED] Viaje {doc['codigo_ruta']} ya existe, se omite.")
    print(f"[SEED] Proceso finalizado. Documentos nuevos: {insertados}")


if __name__ == "__main__":
    main()
```

### test_mvp.py

```python
# test_mvp.py
# Prueba el ciclo CRUD completo de la API sin necesidad de MongoDB.
# Usa mongomock (una base en memoria) en lugar de la conexión real, así que
# se puede correr en cualquier equipo con: python test_mvp.py
#
# Cada paso comprueba con assert el código HTTP y el resultado esperado.
# Si algo no cuadra, el script corta con AssertionError en vez de seguir.

import mongomock

# Base simulada con el mismo índice único que usa la colección real.
_coleccion = mongomock.MongoClient()["logitrack_global"]["viajes_monitoreo"]
_coleccion.create_index("codigo_ruta", unique=True)


def get_collection_de_prueba():
    return _coleccion


# Inyectamos la base simulada antes de importar el resto de los módulos,
# para que todos usen esta colección y no intenten conectarse a MongoDB.
import config.database as db
db.get_collection = get_collection_de_prueba
import models.viaje_model as vm
vm.get_collection = get_collection_de_prueba

from fastapi.testclient import TestClient
import seed
from views.viaje_view import app

cliente = TestClient(app)
CODIGO = "RT-GLOBAL-2026-11D"


print("1. SEED: cargar datos de prueba")
seed.main()

print("2. READ: GET /viajes")
r = cliente.get("/viajes")
assert r.status_code == 200, r.text
assert len(r.json()) == 3, f"se esperaban 3 viajes, hay {len(r.json())}"
print(f"   OK - {len(r.json())} viajes en la colección")

print("3. READ: GET /viajes/RT-GLOBAL-2026-99A")
r = cliente.get("/viajes/RT-GLOBAL-2026-99A")
assert r.status_code == 200, r.text
viaje = r.json()
assert viaje["conductor"]["nombre"] == "Juan"
assert len(viaje["telemetria_iot"]) == 2
print(f"   OK - conductor: {viaje['conductor']['nombre']} "
      f"{viaje['conductor']['primer_apellido']}, "
      f"lecturas IoT: {len(viaje['telemetria_iot'])}")

print("4. CREATE: POST /viajes")
nuevo = {
    "codigo_ruta": CODIGO,
    "origen": "Buenos Aires, Argentina",
    "destino": "Montevideo, Uruguay",
    "tiempo_estimado_dias": 1.0,
    "estado_viaje": "PROGRAMADO",
    "centro_contacto_despacho": {"nombre_contacto": "Lucía Fernández",
                                 "telefono": "+549114455667", "ciudad": "Buenos Aires"},
    "vehiculo": {"vin": "9BM958074GB000003", "patente": "MNOP-78", "marca": "Iveco",
                 "modelo": "S-Way", "ano_fabricacion": 2025, "tipo_combustible": "GNL",
                 "capacidad_carga_max_Kg": 32000},
    "conductor": {"rut_id": "AR-30111222", "nombre": "Marta", "primer_apellido": "Gómez",
                  "nacionalidad": "Argentina",
                  "licencia": {"tipo": "E1", "fecha_vencimiento": "2030-01-15"}},
}
r = cliente.post("/viajes", json=nuevo)
assert r.status_code == 201, r.text
assert r.json()["codigo_ruta"] == CODIGO
print(f"   OK - {r.json()}")

print("5. CREATE con código repetido (debe rechazarlo)")
r = cliente.post("/viajes", json=nuevo)
assert r.status_code == 400, r.text
print(f"   OK - HTTP 400: {r.json()['detail']}")

print("6. CREATE con VIN inválido (debe rechazarlo)")
vin_malo = dict(nuevo, codigo_ruta="RT-GLOBAL-2026-22E")
vin_malo["vehiculo"] = dict(nuevo["vehiculo"], vin="CORTO")
r = cliente.post("/viajes", json=vin_malo)
assert r.status_code == 400, r.text
print(f"   OK - HTTP 400: {r.json()['detail']}")

print("7. UPDATE: POST telemetría ($push en el arreglo)")
lectura = {"latitud": -34.6037, "longitud": -58.3816, "velocidad_kmh": 72.5,
           "temperatura_motor_c": 90.1, "nivel_combustible_porcentaje": 88.0,
           "alerta_sistema": None}
r = cliente.post(f"/viajes/{CODIGO}/telemetria", json=lectura)
assert r.status_code == 200, r.text
assert len(r.json()["telemetria_iot"]) == 1
print(f"   OK - lecturas IoT después del $push: {len(r.json()['telemetria_iot'])}")

print("8. UPDATE: telemetría con velocidad imposible (debe rechazarla)")
mala = dict(lectura, velocidad_kmh=450.0)
r = cliente.post(f"/viajes/{CODIGO}/telemetria", json=mala)
assert r.status_code == 400, r.text
print(f"   OK - HTTP 400: {r.json()['detail']}")

print("9. UPDATE: PATCH estado a EN_TRANSITO")
r = cliente.patch(f"/viajes/{CODIGO}/estado", json={"estado_viaje": "EN_TRANSITO"})
assert r.status_code == 200, r.text
assert r.json()["estado_viaje"] == "EN_TRANSITO"
print(f"   OK - {r.json()}")

print("10. UPDATE: estado inválido (debe rechazarlo)")
r = cliente.patch(f"/viajes/{CODIGO}/estado", json={"estado_viaje": "VOLANDO"})
assert r.status_code == 400, r.text
print(f"   OK - HTTP 400: {r.json()['detail']}")

print("11. UPDATE: agregar capacitación al conductor")
cap = {"centro_educativo": "LogiTrack Academy", "ano": 2026,
       "certificacion_obtenida": "Manejo Defensivo Internacional"}
r = cliente.post(f"/viajes/{CODIGO}/conductor/capacitaciones", json=cap)
assert r.status_code == 200, r.text
print(f"   OK - {r.json()}")

print("12. DELETE: eliminar el viaje")
r = cliente.delete(f"/viajes/{CODIGO}")
assert r.status_code == 200, r.text
print(f"   OK - {r.json()}")

print("13. READ después del DELETE (debe dar 404)")
r = cliente.get(f"/viajes/{CODIGO}")
assert r.status_code == 404, r.text
print(f"   OK - HTTP 404: {r.json()['detail']}")

print("\nTodas las pruebas CRUD se ejecutaron correctamente")
```

### requirements.txt

```text
fastapi
uvicorn
pymongo
python-dotenv
pydantic
mongomock
httpx
```

### .env.example

```ini
# Copiar este archivo como ".env" y completar con credenciales reales.
# NUNCA subir el archivo .env al repositorio (está en .gitignore).
MONGO_URI=mongodb://usuario_app:CLAVE_SEGURA@localhost:27017/?authSource=admin
MONGO_DB=logitrack_global
MONGO_COLL=viajes_monitoreo
```

### .gitignore

```text
venv/
__pycache__/
*.pyc
.env
```
