"""Router de Bitácora de Recetas (CU-08).

Implementa las 5 capas de protección:
1. CORS Restringido (en main.py)
2. Secreto Compartido vía cabecera 'X-App-Client-Key'
3. Honeypot Anti-Bot con campo 'website_hp'
4. Rate Limiting en memoria (máximo 5 peticiones por minuto por IP)
5. Cuota por dispositivo (máximo 15 recetas por dispositivo_uuid)
"""

import os
import time
from collections import defaultdict
from typing import Dict, List
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from api.dependencies import get_db_session
from api.schemas import RecipeCreateRequest, RecipeResponse
from application.manage_recipes import ManageRecipesUseCase, RecetaCreateDTO

router = APIRouter(prefix="/api/v1/recetas", tags=["Recetas"])

# Configuración de secreto de cliente
APP_CLIENT_KEY = os.getenv("APP_CLIENT_KEY", "cafesitios-client-key-mvp-2026")

# Rate limiting simple en memoria (5 peticiones por minuto por IP)
_recipe_rate_limit: Dict[str, List[float]] = defaultdict(list)
RATE_LIMIT_WINDOW_SECONDS = 60
RATE_LIMIT_MAX_REQUESTS = 5


def _get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "127.0.0.1"


def _check_rate_limit(client_ip: str) -> None:
    now = time.time()
    timestamps = _recipe_rate_limit[client_ip]
    # Limpiar entradas antiguas
    _recipe_rate_limit[client_ip] = [t for t in timestamps if now - t < RATE_LIMIT_WINDOW_SECONDS]
    if len(_recipe_rate_limit[client_ip]) >= RATE_LIMIT_MAX_REQUESTS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Límite de solicitudes superado (máximo 5 por minuto). Intente más tarde."
        )
    _recipe_rate_limit[client_ip].append(now)


@router.post(
    "",
    response_model=RecipeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Guardar o sincronizar receta en la nube (CU-08)",
    description="Almacena una receta barista con 5 capas de validación y seguridad."
)
def create_recipe(
    recipe_data: RecipeCreateRequest,
    request: Request,
    x_app_client_key: str = Header(..., alias="X-App-Client-Key", description="Clave de cliente de la app"),
    db_session: Session = Depends(get_db_session)
) -> RecipeResponse:
    # Capa 2: Secreto compartido
    if x_app_client_key != APP_CLIENT_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Clave de cliente no autorizada (X-App-Client-Key inválida)."
        )

    # Capa 3: Honeypot Anti-Bot
    if recipe_data.website_hp:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Petición rechazada por detección de bot."
        )

    # Capa 4: Rate Limiting
    client_ip = _get_client_ip(request)
    _check_rate_limit(client_ip)

    # Capa 5: Cuota por dispositivo en caso de uso
    use_case = ManageRecipesUseCase(session=db_session)
    try:
        nueva_receta = use_case.create_receta(
            RecetaCreateDTO(
                dispositivo_uuid=recipe_data.dispositivo_uuid,
                producto_id=recipe_data.producto_id,
                nombre_receta=recipe_data.nombre_receta,
                metodo=recipe_data.metodo,
                dosis_cafe_g=recipe_data.dosis_cafe_g,
                agua_ml=recipe_data.agua_ml,
                ratio=recipe_data.ratio,
                molino_usado=recipe_data.molino_usado,
                grosor_molienda=recipe_data.grosor_molienda,
                temperatura_c=recipe_data.temperatura_c,
                tiempo_total_s=recipe_data.tiempo_total_s,
                calificacion_1_10=recipe_data.calificacion_1_10,
                reintentar=recipe_data.reintentar,
                notas_catado=recipe_data.notas_catado,
                catacion_sca=recipe_data.catacion_sca.model_dump() if recipe_data.catacion_sca else None,
                puntuacion_sca_total=recipe_data.puntuacion_sca_total,
            )
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    return RecipeResponse(
        id=nueva_receta.id,
        dispositivo_uuid=nueva_receta.dispositivo_uuid,
        nombre_receta=nueva_receta.nombre_receta,
        metodo=nueva_receta.metodo,
        dosis_cafe_g=float(nueva_receta.dosis_cafe_g),
        agua_ml=float(nueva_receta.agua_ml),
        ratio=nueva_receta.ratio,
        molino_usado=nueva_receta.molino_usado,
        grosor_molienda=nueva_receta.grosor_molienda,
        temperatura_c=nueva_receta.temperatura_c,
        tiempo_total_s=nueva_receta.tiempo_total_s,
        calificacion_1_10=nueva_receta.calificacion_1_10,
        reintentar=bool(nueva_receta.reintentar),
        notas_catado=nueva_receta.notas_catado,
        catacion_sca=nueva_receta.catacion_sca,
        puntuacion_sca_total=float(nueva_receta.puntuacion_sca_total) if nueva_receta.puntuacion_sca_total is not None else None,
        fecha_creacion=nueva_receta.fecha_creacion,
    )


@router.get(
    "",
    response_model=List[RecipeResponse],
    status_code=status.HTTP_200_OK,
    summary="Listar recetas de un dispositivo (CU-08)",
    description="Devuelve las recetas guardadas para un UUID de dispositivo."
)
def list_recipes(
    dispositivo_uuid: str,
    db_session: Session = Depends(get_db_session)
) -> List[RecipeResponse]:
    use_case = ManageRecipesUseCase(session=db_session)
    recetas = use_case.list_by_device(dispositivo_uuid)
    return [
        RecipeResponse(
            id=r.id,
            dispositivo_uuid=r.dispositivo_uuid,
            nombre_receta=r.nombre_receta,
            metodo=r.metodo,
            dosis_cafe_g=float(r.dosis_cafe_g),
            agua_ml=float(r.agua_ml),
            ratio=r.ratio,
            molino_usado=r.molino_usado,
            grosor_molienda=r.grosor_molienda,
            temperatura_c=r.temperatura_c,
            tiempo_total_s=r.tiempo_total_s,
            calificacion_1_10=r.calificacion_1_10,
            reintentar=bool(r.reintentar),
            notas_catado=r.notas_catado,
            catacion_sca=r.catacion_sca,
            puntuacion_sca_total=float(r.puntuacion_sca_total) if r.puntuacion_sca_total is not None else None,
            fecha_creacion=r.fecha_creacion,
        )
        for r in recetas
    ]

