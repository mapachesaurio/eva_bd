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
