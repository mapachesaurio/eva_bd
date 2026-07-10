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
