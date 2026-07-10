# config/esquema.py
# Inicialización del esquema de la colección viajes_monitoreo desde Python.
# Crea (si faltan) la colección con su validador $jsonSchema estricto y los
# índices de rendimiento. Es idempotente: correrlo varias veces no rompe nada.
#
# IMPORTANTE: este esquema es la traducción a Python de scripts/crear_esquema.js.
# Ambos definen la MISMA estructura y deben mantenerse sincronizados: si cambia
# uno, actualizar el otro.

from config.database import get_db, MONGO_COLL

# Validador $jsonSchema estricto (requisitos G.7 y G.8). Espejo del .js.
VALIDADOR = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": ["codigo_ruta", "origen", "destino", "estado_viaje", "vehiculo", "conductor"],
        "properties": {
            "codigo_ruta": {
                "bsonType": "string",
                "description": "String único identificador de la ruta logística. Obligatorio.",
            },
            "origen": {"bsonType": "string"},
            "destino": {"bsonType": "string"},
            "tiempo_estimado_dias": {"bsonType": ["double", "int"]},
            "estado_viaje": {
                "enum": ["PROGRAMADO", "EN_TRANSITO", "FINALIZADO", "CANCELADO"],
                "description": "Restringido a los estados operativos de la última milla.",
            },
            "centro_contacto_despacho": {
                "bsonType": "object",
                "properties": {
                    "nombre_contacto": {"bsonType": "string"},
                    "telefono": {"bsonType": "string"},
                    "ciudad": {"bsonType": "string"},
                    "observaciones_logistica": {"bsonType": "string"},
                },
            },
            "vehiculo": {
                "bsonType": "object",
                "required": ["vin", "patente", "marca", "modelo", "capacidad_carga_max_Kg"],
                "properties": {
                    "vin": {"bsonType": "string", "minLength": 17, "maxLength": 17},
                    "patente": {"bsonType": "string"},
                    "marca": {"bsonType": "string"},
                    "modelo": {"bsonType": "string"},
                    "ano_fabricacion": {"bsonType": "int"},
                    "tipo_combustible": {"bsonType": "string"},
                    "capacidad_carga_max_Kg": {"bsonType": "int", "minimum": 1},
                    "observaciones_mecanicas": {"bsonType": "string"},
                },
            },
            "conductor": {
                "bsonType": "object",
                "required": ["rut_id", "nombre", "primer_apellido", "nacionalidad"],
                "properties": {
                    "rut_id": {"bsonType": "string"},
                    "nombre": {"bsonType": "string"},
                    "primer_apellido": {"bsonType": "string"},
                    "nacionalidad": {"bsonType": "string"},
                    "licencia": {
                        "bsonType": "object",
                        "properties": {
                            "tipo": {"bsonType": "string"},
                            "fecha_vencimiento": {"bsonType": ["date", "string"]},
                        },
                    },
                    "capacitaciones": {
                        "bsonType": "array",
                        "items": {
                            "bsonType": "object",
                            "properties": {
                                "centro_educativo": {"bsonType": "string"},
                                "ano": {"bsonType": "int"},
                                "certificacion_obtenida": {"bsonType": "string"},
                            },
                        },
                    },
                    "observaciones_desempeño": {"bsonType": "string"},
                    "jerarquia": {
                        "bsonType": "object",
                        "properties": {
                            "supervisor_id": {"bsonType": ["objectId", "string"]},
                            "nombres_conductores_supervisados": {
                                "bsonType": "array",
                                "items": {"bsonType": "string"},
                            },
                        },
                    },
                },
            },
            "telemetria_iot": {
                "bsonType": "array",
                "items": {
                    "bsonType": "object",
                    "required": [
                        "timestamp",
                        "velocidad_kmh",
                        "temperatura_motor_c",
                        "nivel_combustible_porcentaje",
                    ],
                    "properties": {
                        "timestamp": {"bsonType": "date"},
                        "ubicacion": {
                            "bsonType": "object",
                            "properties": {
                                "tipo": {"enum": ["Point"]},
                                "coordenadas": {"bsonType": "array", "items": {"bsonType": "double"}},
                            },
                        },
                        "velocidad_kmh": {"bsonType": ["double", "int"]},
                        "temperatura_motor_c": {"bsonType": ["double", "int"]},
                        "nivel_combustible_porcentaje": {"bsonType": ["double", "int"]},
                        "alerta_sistema": {"bsonType": ["string", "null"]},
                    },
                },
            },
        },
    }
}


def inicializar_esquema():
    """Crea la colección con validador estricto e índices si todavía no existen.
    Idempotente: si ya está creada, no la recrea; los índices se aseguran igual."""
    db = get_db()

    if MONGO_COLL not in db.list_collection_names():
        db.create_collection(
            MONGO_COLL,
            validator=VALIDADOR,
            validationLevel="strict",   # valida TODA inserción y actualización
            validationAction="error",   # rechaza documentos inválidos (no solo advierte)
        )
        print(f"[ESQUEMA] Colección {MONGO_COLL} creada con validador estricto.")
    else:
        # La colección ya existe: aseguramos el validador con collMod. No toca
        # los documentos existentes, solo valida las escrituras futuras. Así, si
        # la colección se creó plana (p. ej. por un insert), igual queda estricta.
        db.command(
            "collMod",
            MONGO_COLL,
            validator=VALIDADOR,
            validationLevel="strict",
            validationAction="error",
        )
        print(f"[ESQUEMA] Colección {MONGO_COLL} ya existe, validador asegurado.")

    # Índices estratégicos para la carga proyectada de 20.000 req/min (G.7).
    # create_index es idempotente: si ya existe con el mismo spec, es un no-op.
    coleccion = db[MONGO_COLL]
    coleccion.create_index("codigo_ruta", unique=True)
    coleccion.create_index("vehiculo.vin")
    coleccion.create_index("conductor.rut_id")
    coleccion.create_index("estado_viaje")
    coleccion.create_index([("telemetria_iot.timestamp", -1)])
    print("[ESQUEMA] Índices asegurados.")
