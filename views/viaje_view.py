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
