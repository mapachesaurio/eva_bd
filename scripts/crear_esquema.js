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
