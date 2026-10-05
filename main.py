"""
Recetario API — Biblioteca de recetas con FastAPI.

CRUD completo + endpoints extra:
  - GET /recetas/buscar          -> búsqueda por texto (nombre, descripción, ingredientes)
  - GET /recetas/sugerencias     -> "¿Qué puedo cocinar con lo que tengo?"
  - GET /recetas/estadisticas    -> resumen del recetario
  - PATCH /recetas/{id}/favorita -> marcar / desmarcar como favorita

Ejecutar:  uvicorn main:app --reload
Docs:      http://127.0.0.1:8000/docs
"""

from collections import Counter
from enum import Enum
from typing import Optional

from fastapi import FastAPI, HTTPException, Query, Response, status
from pydantic import BaseModel, ConfigDict, Field, field_validator

app = FastAPI(
    title="Recetario API",
    description="Biblioteca de recetas con CRUD, búsqueda, sugerencias por ingredientes y estadísticas.",
    version="1.0.0",
)


# --------------------------------------------------------------------------- #
# Modelos Pydantic
# --------------------------------------------------------------------------- #
class Dificultad(str, Enum):
    facil = "facil"
    media = "media"
    dificil = "dificil"


class RecetaBase(BaseModel):
    """Campos que el cliente envía al crear o actualizar una receta."""

    model_config = ConfigDict(str_strip_whitespace=True)

    nombre: str = Field(..., min_length=2, max_length=80, examples=["Chilaquiles verdes"])
    descripcion: Optional[str] = Field(None, max_length=300)
    categoria: str = Field(..., min_length=2, max_length=40, examples=["desayuno"])
    ingredientes: list[str] = Field(..., min_length=1, examples=[["tortilla", "salsa verde", "queso"]])
    pasos: list[str] = Field(..., min_length=1)
    tiempo_minutos: int = Field(..., gt=0, le=1440, description="Tiempo total de preparación")
    porciones: int = Field(2, ge=1, le=50)
    dificultad: Dificultad = Dificultad.facil
    favorita: bool = False

    @field_validator("ingredientes")
    @classmethod
    def normalizar_ingredientes(cls, v: list[str]) -> list[str]:
        limpios = [i.strip().lower() for i in v if i and i.strip()]
        if not limpios:
            raise ValueError("Debe haber al menos un ingrediente no vacío")
        return limpios

    @field_validator("pasos")
    @classmethod
    def limpiar_pasos(cls, v: list[str]) -> list[str]:
        limpios = [p.strip() for p in v if p and p.strip()]
        if not limpios:
            raise ValueError("Debe haber al menos un paso no vacío")
        return limpios

    @field_validator("categoria")
    @classmethod
    def categoria_minuscula(cls, v: str) -> str:
        return v.lower()


class Receta(RecetaBase):
    """Receta tal como la devuelve la API (incluye el id)."""

    id: int


# --------------------------------------------------------------------------- #
# "Base de datos" en memoria
# --------------------------------------------------------------------------- #
db: dict[int, Receta] = {}
_siguiente_id = 1


def _guardar(datos: RecetaBase, receta_id: Optional[int] = None) -> Receta:
    global _siguiente_id
    if receta_id is None:
        receta_id = _siguiente_id
        _siguiente_id += 1
    receta = Receta(id=receta_id, **datos.model_dump())
    db[receta_id] = receta
    return receta


def _nombre_duplicado(nombre: str, ignorar_id: Optional[int] = None) -> bool:
    return any(
        r.nombre.lower() == nombre.lower() and r.id != ignorar_id for r in db.values()
    )


def _obtener_o_404(receta_id: int) -> Receta:
    receta = db.get(receta_id)
    if receta is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No existe una receta con id {receta_id}",
        )
    return receta


def _cargar_datos_iniciales() -> None:
    semilla = [
        RecetaBase(
            nombre="Chilaquiles verdes",
            descripcion="Totopos bañados en salsa verde con queso y crema.",
            categoria="desayuno",
            ingredientes=["tortilla", "tomate verde", "chile serrano", "cebolla", "queso fresco", "crema"],
            pasos=["Freír los totopos.", "Licuar y hervir la salsa.", "Mezclar y servir con queso y crema."],
            tiempo_minutos=30,
            porciones=2,
            dificultad=Dificultad.facil,
            favorita=True,
        ),
        RecetaBase(
            nombre="Guacamole",
            descripcion="Clásico guacamole con limón y cilantro.",
            categoria="botana",
            ingredientes=["aguacate", "jitomate", "cebolla", "cilantro", "limón", "chile serrano", "sal"],
            pasos=["Machacar los aguacates.", "Picar el resto de los ingredientes.", "Mezclar y sazonar con limón y sal."],
            tiempo_minutos=15,
            porciones=4,
            dificultad=Dificultad.facil,
        ),
        RecetaBase(
            nombre="Mole poblano",
            descripcion="Mole tradicional con pollo, chiles y chocolate.",
            categoria="plato fuerte",
            ingredientes=["pollo", "chile ancho", "chile pasilla", "chile mulato", "chocolate", "ajonjolí", "cebolla", "ajo", "jitomate"],
            pasos=[
                "Cocer el pollo.",
                "Tostar chiles, semillas y especias.",
                "Moler todo hasta obtener una pasta.",
                "Cocinar la pasta con caldo y chocolate.",
                "Servir el pollo bañado en mole.",
            ],
            tiempo_minutos=180,
            porciones=8,
            dificultad=Dificultad.dificil,
            favorita=True,
        ),
    ]
    for datos in semilla:
        _guardar(datos)


_cargar_datos_iniciales()


# --------------------------------------------------------------------------- #
# Raíz
# --------------------------------------------------------------------------- #
@app.get("/", tags=["General"])
def raiz():
    return {"api": "Recetario API", "version": app.version, "docs": "/docs"}


# --------------------------------------------------------------------------- #
# CRUD
# --------------------------------------------------------------------------- #
@app.post("/recetas", response_model=Receta, status_code=status.HTTP_201_CREATED, tags=["CRUD"])
def crear_receta(datos: RecetaBase):
    if _nombre_duplicado(datos.nombre):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Ya existe una receta llamada '{datos.nombre}'",
        )
    return _guardar(datos)


@app.get("/recetas", response_model=list[Receta], tags=["CRUD"])
def listar_recetas(
    categoria: Optional[str] = Query(None, description="Filtra por categoría"),
    dificultad: Optional[Dificultad] = Query(None, description="Filtra por dificultad"),
    max_tiempo: Optional[int] = Query(None, gt=0, description="Tiempo máximo en minutos"),
    favorita: Optional[bool] = Query(None, description="Solo favoritas (true) o no favoritas (false)"),
):
    resultado = list(db.values())
    if categoria is not None:
        resultado = [r for r in resultado if r.categoria == categoria.lower()]
    if dificultad is not None:
        resultado = [r for r in resultado if r.dificultad == dificultad]
    if max_tiempo is not None:
        resultado = [r for r in resultado if r.tiempo_minutos <= max_tiempo]
    if favorita is not None:
        resultado = [r for r in resultado if r.favorita == favorita]
    return resultado


# --- Endpoints extra (van ANTES de /recetas/{receta_id} para no chocar con la ruta dinámica) ---
@app.get("/recetas/buscar", response_model=list[Receta], tags=["Extra"])
def buscar_recetas(q: str = Query(..., min_length=2, description="Texto a buscar")):
    """Busca en nombre, descripción e ingredientes (sin distinguir mayúsculas)."""
    texto = q.lower()
    return [
        r
        for r in db.values()
        if texto in r.nombre.lower()
        or texto in (r.descripcion or "").lower()
        or any(texto in i for i in r.ingredientes)
    ]


@app.get("/recetas/sugerencias", tags=["Extra"])
def sugerir_recetas(
    ingredientes: str = Query(..., description="Ingredientes que tienes, separados por coma. Ej: tomate,cebolla,queso"),
):
    """
    '¿Qué puedo cocinar con lo que tengo?'
    Devuelve las recetas ordenadas por el porcentaje de ingredientes que ya tienes,
    indicando cuáles te faltan.
    """
    disponibles = [i.strip().lower() for i in ingredientes.split(",") if i.strip()]
    if not disponibles:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Indica al menos un ingrediente",
        )

    sugerencias = []
    for receta in db.values():
        tengo = [ing for ing in receta.ingredientes if any(d in ing for d in disponibles)]
        if not tengo:
            continue
        faltan = [ing for ing in receta.ingredientes if ing not in tengo]
        sugerencias.append(
            {
                "id": receta.id,
                "nombre": receta.nombre,
                "cobertura_pct": round(len(tengo) / len(receta.ingredientes) * 100, 1),
                "ingredientes_que_tienes": tengo,
                "ingredientes_que_faltan": faltan,
            }
        )
    sugerencias.sort(key=lambda s: s["cobertura_pct"], reverse=True)
    return {"consultados": disponibles, "total": len(sugerencias), "sugerencias": sugerencias}


@app.get("/recetas/estadisticas", tags=["Extra"])
def estadisticas():
    """Resumen del recetario."""
    recetas = list(db.values())
    if not recetas:
        return {"total_recetas": 0}

    conteo_ingredientes = Counter(i for r in recetas for i in r.ingredientes)
    mas_rapida = min(recetas, key=lambda r: r.tiempo_minutos)
    return {
        "total_recetas": len(recetas),
        "favoritas": sum(r.favorita for r in recetas),
        "tiempo_promedio_minutos": round(sum(r.tiempo_minutos for r in recetas) / len(recetas), 1),
        "receta_mas_rapida": {"id": mas_rapida.id, "nombre": mas_rapida.nombre, "tiempo_minutos": mas_rapida.tiempo_minutos},
        "por_categoria": dict(Counter(r.categoria for r in recetas)),
        "por_dificultad": dict(Counter(r.dificultad.value for r in recetas)),
        "ingredientes_mas_usados": [
            {"ingrediente": ing, "veces": n} for ing, n in conteo_ingredientes.most_common(3)
        ],
    }


@app.get("/recetas/{receta_id}", response_model=Receta, tags=["CRUD"])
def obtener_receta(receta_id: int):
    return _obtener_o_404(receta_id)


@app.put("/recetas/{receta_id}", response_model=Receta, tags=["CRUD"])
def actualizar_receta(receta_id: int, datos: RecetaBase):
    _obtener_o_404(receta_id)
    if _nombre_duplicado(datos.nombre, ignorar_id=receta_id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Ya existe otra receta llamada '{datos.nombre}'",
        )
    return _guardar(datos, receta_id=receta_id)


@app.delete("/recetas/{receta_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["CRUD"])
def eliminar_receta(receta_id: int):
    _obtener_o_404(receta_id)
    del db[receta_id]
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.patch("/recetas/{receta_id}/favorita", response_model=Receta, tags=["Extra"])
def alternar_favorita(receta_id: int):
    """Marca o desmarca una receta como favorita."""
    receta = _obtener_o_404(receta_id)
    receta.favorita = not receta.favorita
    return receta
