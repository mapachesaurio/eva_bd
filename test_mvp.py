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
