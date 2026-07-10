# LogiTrack_Global - MVP de Monitoreo de Flotas e IoT (MongoDB + Python Modelo Vista Controlador)

Backend del MVP de la plataforma de monitoreo de flotas LogiTrack_Global
(Evaluación 6, Unidad 4, Bases de Datos No Estructuradas, TI3032).

Integrantes: Felipe Cisternas, Vicente Navarro, Felipe Martínez

Gestiona viajes de una flota de camiones sobre MongoDB, guardando en un mismo documento el
vehículo, el conductor y las lecturas de telemetría IoT. Ofrece dos interfaces sobre la misma
lógica: una **app de consola** (`main.py`) y una **API REST** hecha con FastAPI.

## Estructura del proyecto

```
logitrack_mvc/
├── config/
│   └── database.py            Conexión a MongoDB (lee .env, pool de conexiones)
├── models/
│   └── viaje_model.py         Modelo: consultas PyMongo (CRUD)
├── controllers/
│   ├── viaje_controller.py    Controlador de negocio: reglas y validaciones
│   └── consola_controller.py  Controlador de la consola: flujo del menú
├── views/
│   ├── viaje_view.py          Vista web: endpoints FastAPI + esquemas Pydantic
│   └── consola_view.py        Vista de consola: menú y entrada/salida por teclado
├── scripts/
│   └── crear_esquema.js       Script de mongosh: crea la colección con validador e índices
├── main.py                    App de consola (punto de entrada del menú)
├── seed.py                    Carga 3 viajes de ejemplo
├── test_mvp.py                Prueba el CRUD completo con una base simulada en memoria
├── requirements.txt           Dependencias
├── .env.example               Plantilla de credenciales (copiar como .env)
└── venv/                      Entorno virtual (no se sube a git)
```

Sigue el patrón MVC en las dos interfaces: la **vista** (web o consola) se encarga de la
entrada y salida, el **controlador** aplica las reglas de negocio y el **modelo** es el único
que toca la base de datos. `main.py` no tiene lógica: solo arranca la consola.

## Requisitos

- Python 3.10 o superior.
- MongoDB para la consola y la API. La prueba automática (`test_mvp.py`) no lo necesita.

## Instalación

Los comandos se ejecutan desde la carpeta raíz del proyecto (`logitrack_mvc/`).

1. Crear el entorno virtual:

   ```
   python -m venv venv
   ```

2. Activarlo:

   ```
   .\venv\Scripts\activate      (Windows)
   source venv/bin/activate      (Linux o macOS)
   ```

3. Instalar las dependencias:

   ```
   pip install -r requirements.txt
   ```

4. Crear el archivo de credenciales copiando la plantilla:

   ```
   copy .env.example .env       (Windows)
   cp .env.example .env          (Linux o macOS)
   ```

   Después abrir `.env` y poner la URI y credenciales reales de tu MongoDB.

El archivo `.env` tiene tres variables:

- `MONGO_URI`: cadena de conexión (por defecto `mongodb://localhost:27017`).
- `MONGO_DB`: nombre de la base de datos (`logitrack_global`).
- `MONGO_COLL`: nombre de la colección (`viajes_monitoreo`).

## Preparar la base de datos

Con MongoDB corriendo, y una sola vez, crear la colección con su validador e índices:

```
mongosh "mongodb://localhost:27017" scripts/crear_esquema.js   # colección con validador e índices
```

No es necesario ejecutar `python seed.py` a mano: al arrancar con `python main.py`, si la base
está vacía se pregunta `¿Querés poblar la base de datos? (si/no)` y, respondiendo `si`, se cargan
los 3 viajes de ejemplo automáticamente. `seed.py` sigue disponible por si se quiere poblar aparte.

Importante: `crear_esquema.js` se ejecuta con `mongosh`, como arriba. No se importa con
`mongoimport` ni se pega como documento en Compass; si se hace eso, cada línea del archivo se
guarda como un documento y la colección queda llena de basura.

## Uso

### Opción 1 - API web (FastAPI) con `main.py`

```
python main.py
```

Verifica si la base ya fue poblada; si está vacía pregunta `¿Querés poblar la base de datos?
(si/no)` (respuesta validada, solo `si` o `no`) y luego levanta el servidor uvicorn en
http://127.0.0.1:8000.

También se puede levantar el servidor directamente (sin el chequeo de seed):

```
uvicorn views.viaje_view:app --reload
```

La documentación interactiva (Swagger UI) queda en http://127.0.0.1:8000/docs, donde se pueden
probar todos los endpoints desde el navegador. La raíz http://127.0.0.1:8000 no tiene página
(devuelve "Not Found"); hay que entrar a `/docs`.

### Opción 3 - Prueba automática sin MongoDB

```
python test_mvp.py
```

Usa una base simulada en memoria (mongomock) y ejecuta el ciclo CRUD completo con
verificaciones. No necesita MongoDB ni haber corrido los pasos anteriores. Al terminar debe
imprimir "Todas las pruebas CRUD se ejecutaron correctamente".

## Endpoints de la API

Base: `http://127.0.0.1:8000`

| Método | Ruta | Operación |
|---|---|---|
| POST   | `/viajes` | Crear un viaje (vehículo + conductor + ruta) |
| GET    | `/viajes?estado=` | Listar viajes, con filtro opcional por estado |
| GET    | `/viajes/{codigo_ruta}` | Ver un viaje puntual |
| POST   | `/viajes/{codigo_ruta}/telemetria` | Agregar una lectura IoT al viaje |
| PATCH  | `/viajes/{codigo_ruta}/estado` | Cambiar el estado del viaje |
| POST   | `/viajes/{codigo_ruta}/conductor/capacitaciones` | Agregar una capacitación al conductor |
| DELETE | `/viajes/{codigo_ruta}` | Eliminar el viaje |

Reglas que aplica el controlador:

- Estados permitidos: `PROGRAMADO`, `EN_TRANSITO`, `FINALIZADO`, `CANCELADO`.
- El VIN del vehículo debe tener 17 caracteres.
- Telemetría: velocidad entre 0 y 200 km/h, temperatura entre -40 y 150 °C, combustible entre
  0 y 100 %.
- `codigo_ruta` es único; si se repite, la API responde 400.
- El `timestamp` de cada lectura lo pone el servidor en UTC.

### Ejemplos

Crear un viaje:

```
curl -X POST http://127.0.0.1:8000/viajes -H "Content-Type: application/json" -d '{
  "codigo_ruta": "RT-GLOBAL-2026-11D",
  "origen": "Buenos Aires, Argentina",
  "destino": "Montevideo, Uruguay",
  "tiempo_estimado_dias": 1.0,
  "estado_viaje": "PROGRAMADO",
  "centro_contacto_despacho": {
    "nombre_contacto": "Lucía Fernández", "telefono": "+549114455667", "ciudad": "Buenos Aires"
  },
  "vehiculo": {
    "vin": "9BM958074GB000003", "patente": "MNOP-78", "marca": "Iveco", "modelo": "S-Way",
    "ano_fabricacion": 2025, "tipo_combustible": "GNL", "capacidad_carga_max_Kg": 32000
  },
  "conductor": {
    "rut_id": "AR-30111222", "nombre": "Marta", "primer_apellido": "Gómez",
    "nacionalidad": "Argentina",
    "licencia": {"tipo": "E1", "fecha_vencimiento": "2030-01-15"}
  }
}'
```

Listar viajes (con o sin filtro):

```
curl http://127.0.0.1:8000/viajes
curl "http://127.0.0.1:8000/viajes?estado=EN_TRANSITO"
```

Ver un viaje:

```
curl http://127.0.0.1:8000/viajes/RT-GLOBAL-2026-11D
```

Registrar una lectura IoT:

```
curl -X POST http://127.0.0.1:8000/viajes/RT-GLOBAL-2026-11D/telemetria \
  -H "Content-Type: application/json" -d '{
  "latitud": -34.6037, "longitud": -58.3816, "velocidad_kmh": 72.5,
  "temperatura_motor_c": 90.1, "nivel_combustible_porcentaje": 88.0, "alerta_sistema": null
}'
```

Cambiar el estado:

```
curl -X PATCH http://127.0.0.1:8000/viajes/RT-GLOBAL-2026-11D/estado \
  -H "Content-Type: application/json" -d '{"estado_viaje": "EN_TRANSITO"}'
```

Agregar una capacitación:

```
curl -X POST http://127.0.0.1:8000/viajes/RT-GLOBAL-2026-11D/conductor/capacitaciones \
  -H "Content-Type: application/json" -d '{
  "centro_educativo": "LogiTrack Academy", "ano": 2026,
  "certificacion_obtenida": "Manejo Defensivo Internacional"
}'
```

Eliminar un viaje:

```
curl -X DELETE http://127.0.0.1:8000/viajes/RT-GLOBAL-2026-11D
```

## Seguridad

- Credenciales en `.env`, fuera del repositorio (está en `.gitignore`).
- Pool de conexiones (`maxPoolSize=50`).
- Manejo de errores de conexión, autenticación y validación de esquema.
- Validador `$jsonSchema` en la colección (`validationAction: "error"`).
- Usuario de aplicación con rol `readWrite` limitado a la base `logitrack_global`.

## Problemas frecuentes

- `ServerSelectionTimeoutError`: MongoDB no está corriendo o la `MONGO_URI` es incorrecta.
- `InvalidURI: Invalid URI scheme`: la `MONGO_URI` debe empezar con `mongodb://`.
- `ModuleNotFoundError` con fastapi, pymongo, etc.: falta activar el venv o instalar las
  dependencias.
- `ModuleNotFoundError: No module named 'controllers'`: estás corriendo el comando desde otra
  carpeta. Hay que ejecutarlo desde la raíz del proyecto.
- La URL http://127.0.0.1:8000 muestra "Not Found": es normal, la interfaz está en `/docs`.
- Si los acentos se ven mal en la consola de Windows: ejecutar `python -X utf8 main.py`.
