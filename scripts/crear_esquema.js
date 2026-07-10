// scripts/crear_esquema.js
// -------------------------
// Script de inicialización del DBMS (ejecutar con mongosh).
// Crea la colección con validador $jsonSchema estricto (requisitos G.7 y G.8)
// y los índices de rendimiento, leyendo la definición desde config/esquema.json.
// Esa es la única fuente del esquema: este script y config/esquema.py la
// consumen, ninguno la redefine.
//
// Uso:  mongosh "mongodb://localhost:27017" scripts/crear_esquema.js

const fs = require("fs");
const path = require("path");

const rutaEsquema = path.join(__dirname, "..", "config", "esquema.json");
const esquema = JSON.parse(fs.readFileSync(rutaEsquema, "utf8"));

const NOMBRE_COLECCION = "viajes_monitoreo";
db = db.getSiblingDB("logitrack_global");

const existe = db.getCollectionNames().indexOf(NOMBRE_COLECCION) !== -1;
if (!existe) {
  db.createCollection(NOMBRE_COLECCION, {
    validator: esquema.validator,
    validationLevel: "strict", // valida toda inserción y actualización
    validationAction: "error", // rechaza documentos inválidos (no solo advierte)
  });
  print("Colección " + NOMBRE_COLECCION + " creada con validador estricto.");
} else {
  // La colección ya existe: se asegura el validador sin tocar los datos.
  db.runCommand({
    collMod: NOMBRE_COLECCION,
    validator: esquema.validator,
    validationLevel: "strict",
    validationAction: "error",
  });
  print("Colección " + NOMBRE_COLECCION + " ya existe, validador asegurado.");
}

// Índices estratégicos para la carga proyectada de 20.000 req/min (G.7).
// createIndex es idempotente: mismo spec = no-op.
esquema.indexes.forEach(function (indice) {
  const opciones = {};
  if (indice.unique) opciones.unique = true;
  db[NOMBRE_COLECCION].createIndex(indice.keys, opciones);
});

print("Índices asegurados.");
