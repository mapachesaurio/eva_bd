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
