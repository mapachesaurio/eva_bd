# config/esquema.py
# Inicialización del esquema de la colección viajes_monitoreo desde Python.
# Crea (si faltan) la colección con su validador $jsonSchema estricto y los
# índices de rendimiento. Es idempotente: ejecutarlo varias veces no rompe nada.
#
# La definición del esquema vive en config/esquema.json (única fuente). Este
# módulo y scripts/crear_esquema.js la consumen; ninguno la redefine.

import json
from pathlib import Path

from config.database import get_db, MONGO_COLL

# Carga la definición del esquema (validador + índices) desde el JSON compartido.
_RUTA_ESQUEMA = Path(__file__).with_name("esquema.json")
with _RUTA_ESQUEMA.open(encoding="utf-8") as archivo:
    _ESQUEMA = json.load(archivo)

VALIDADOR = _ESQUEMA["validator"]


def inicializar_esquema():
    """Crea la colección con validador estricto e índices si todavía no existen.
    Idempotente: si ya está creada, asegura el validador; los índices se
    aseguran igual."""
    db = get_db()

    if MONGO_COLL not in db.list_collection_names():
        db.create_collection(
            MONGO_COLL,
            validator=VALIDADOR,
            validationLevel="strict",   # valida toda inserción y actualización
            validationAction="error",   # rechaza documentos inválidos (no solo advierte)
        )
        print(f"[ESQUEMA] Colección {MONGO_COLL} creada con validador estricto.")
    else:
        # La colección ya existe: se asegura el validador con collMod. No toca
        # los documentos existentes, solo valida las escrituras futuras.
        db.command(
            "collMod",
            MONGO_COLL,
            validator=VALIDADOR,
            validationLevel="strict",
            validationAction="error",
        )
        print(f"[ESQUEMA] Colección {MONGO_COLL} ya existe, validador asegurado.")

    # Índices estratégicos para la carga proyectada de 20.000 req/min (G.7).
    # create_index es idempotente: mismo spec = no-op.
    coleccion = db[MONGO_COLL]
    for indice in _ESQUEMA["indexes"]:
        claves = [(campo, orden) for campo, orden in indice["keys"].items()]
        opciones = {clave: valor for clave, valor in indice.items() if clave != "keys"}
        coleccion.create_index(claves, **opciones)
    print("[ESQUEMA] Índices asegurados.")
