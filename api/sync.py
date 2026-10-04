from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from api.dependencies import get_db_session
from db.database import EstadoSincronizacion

router = APIRouter(prefix="/api/v1/sync", tags=["Sincronización"])


class LastSyncResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    last_sync: Optional[datetime] = None


@router.get(
    "/last",
    response_model=LastSyncResponse,
    status_code=status.HTTP_200_OK,
    summary="Obtener la fecha de la última sincronización exitosa",
    description="Retorna la marca temporal de la última sincronización exitosa de productos ejecutada por el scraper."
)
def get_last_sync(db_session: Session = Depends(get_db_session)) -> dict[str, Optional[datetime]]:
    if not hasattr(db_session, "get"):
        return {"last_sync": None}

    estado = db_session.get(EstadoSincronizacion, 1)
    return {"last_sync": estado.ultima_ejecucion if estado else None}
