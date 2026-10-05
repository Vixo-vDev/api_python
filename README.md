# Recetario API 🍲

API REST sencilla hecha con **FastAPI** para gestionar una biblioteca de recetas.
Los datos se guardan en memoria (se reinician al apagar el servidor) y arranca con 3 recetas de ejemplo.

## Instalación y ejecución

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload
```

Documentación interactiva: http://127.0.0.1:8000/docs

## Endpoints

| Método | Ruta | Descripción | Códigos |
|--------|------|-------------|---------|
| POST   | `/recetas` | Crear receta | 201, 409, 422 |
| GET    | `/recetas` | Listar (filtros: `categoria`, `dificultad`, `max_tiempo`, `favorita`) | 200, 422 |
| GET    | `/recetas/{id}` | Consultar una receta | 200, 404 |
| PUT    | `/recetas/{id}` | Actualizar receta completa | 200, 404, 409, 422 |
| DELETE | `/recetas/{id}` | Eliminar receta | 204, 404 |
| GET    | `/recetas/buscar?q=texto` | Buscar en nombre, descripción e ingredientes | 200, 422 |
| GET    | `/recetas/sugerencias?ingredientes=a,b` | Recetas que puedes preparar con lo que tienes | 200, 422 |
| GET    | `/recetas/estadisticas` | Resumen del recetario | 200 |
| PATCH  | `/recetas/{id}/favorita` | Marcar / desmarcar favorita | 200, 404 |

## Pruebas con curl

```bash
# 1. Crear (201)
curl -i -X POST http://127.0.0.1:8000/recetas \
  -H "Content-Type: application/json" \
  -d '{"nombre":"Quesadillas","categoria":"cena","ingredientes":["tortilla","queso oaxaca"],"pasos":["Calentar el comal","Rellenar y dorar"],"tiempo_minutos":10,"porciones":2}'

# 2. Listar todas (200)
curl -i http://127.0.0.1:8000/recetas

# 3. Listar con filtros (200)
curl -i "http://127.0.0.1:8000/recetas?categoria=desayuno&max_tiempo=45"

# 4. Consultar una por id (200)
curl -i http://127.0.0.1:8000/recetas/1

# 5. Actualizar (200)
curl -i -X PUT http://127.0.0.1:8000/recetas/2 \
  -H "Content-Type: application/json" \
  -d '{"nombre":"Guacamole con totopos","categoria":"botana","ingredientes":["aguacate","limón","sal","totopos"],"pasos":["Machacar el aguacate","Sazonar y servir"],"tiempo_minutos":10,"porciones":4,"dificultad":"facil"}'

# 6. Buscar (200)
curl -i "http://127.0.0.1:8000/recetas/buscar?q=chile"

# 7. Sugerencias por ingredientes (200)
curl -i "http://127.0.0.1:8000/recetas/sugerencias?ingredientes=tomate,cebolla,queso"

# 8. Estadísticas (200)
curl -i http://127.0.0.1:8000/recetas/estadisticas

# 9. Marcar favorita (200)
curl -i -X PATCH http://127.0.0.1:8000/recetas/2/favorita

# 10. Eliminar (204)
curl -i -X DELETE http://127.0.0.1:8000/recetas/3

# --- Pruebas de error ---
# 11. Id inexistente (404)
curl -i http://127.0.0.1:8000/recetas/999

# 12. Datos inválidos (422)
curl -i -X POST http://127.0.0.1:8000/recetas \
  -H "Content-Type: application/json" \
  -d '{"nombre":"X","categoria":"cena","ingredientes":[],"pasos":["a"],"tiempo_minutos":-5}'

# 13. Nombre duplicado (409)
curl -i -X POST http://127.0.0.1:8000/recetas \
  -H "Content-Type: application/json" \
  -d '{"nombre":"Guacamole con totopos","categoria":"botana","ingredientes":["aguacate"],"pasos":["Machacar"],"tiempo_minutos":5}'
```
