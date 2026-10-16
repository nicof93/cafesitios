"""Caso de Uso: Bitácora de Recetas y Sincronización Segura (CU-08).

Gestiona la cuota por dispositivo (máximo 15 recetas) y persistencia.
"""

from dataclasses import dataclass
from typing import List, Optional
from sqlalchemy.orm import Session
from db.database import Receta


@dataclass
class RecetaCreateDTO:
    dispositivo_uuid: str
    nombre_receta: str
    metodo: str
    dosis_cafe_g: float
    agua_ml: float
    producto_id: Optional[int] = None
    ratio: Optional[str] = None
    molino_usado: Optional[str] = None
    grosor_molienda: Optional[str] = None
    temperatura_c: Optional[int] = None
    tiempo_total_s: Optional[int] = None
    calificacion_1_10: Optional[int] = None
    reintentar: bool = True
    notas_catado: Optional[str] = None
    catacion_sca: Optional[dict] = None
    puntuacion_sca_total: Optional[float] = None


class ManageRecipesUseCase:
    MAX_RECETAS_POR_DISPOSITIVO = 15

    def __init__(self, session: Session):
        self.session = session

    def list_by_device(self, dispositivo_uuid: str) -> List[Receta]:
        return (
            self.session.query(Receta)
            .filter(Receta.dispositivo_uuid == dispositivo_uuid)
            .order_by(Receta.fecha_creacion.desc())
            .all()
        )

    def create_receta(self, dto: RecetaCreateDTO) -> Receta:
        # Capa 5: Cuota por dispositivo (Máximo 15 recetas)
        total_existentes = (
            self.session.query(Receta)
            .filter(Receta.dispositivo_uuid == dto.dispositivo_uuid)
            .count()
        )
        if total_existentes >= self.MAX_RECETAS_POR_DISPOSITIVO:
            raise ValueError(
                f"Cuota de recetas excedida. Máximo {self.MAX_RECETAS_POR_DISPOSITIVO} recetas por dispositivo."
            )

        # Validación de ratio si no fue provisto
        ratio_calculado = dto.ratio
        if not ratio_calculado and dto.dosis_cafe_g > 0:
            ratio_num = round(dto.agua_ml / dto.dosis_cafe_g, 1)
            ratio_calculado = f"1:{ratio_num}"

        # Cálculo de puntaje SCA total si se ingresaron atributos de cata Q-Grader (10 indicadores)
        sca_total = dto.puntuacion_sca_total
        if dto.catacion_sca and isinstance(dto.catacion_sca, dict):
            # Suma de los 10 atributos de catación SCA
            score_items = [
                v for k, v in dto.catacion_sca.items()
                if isinstance(v, (int, float)) and k != "puntuacion_total_sca"
            ]
            if score_items and sca_total is None:
                sca_total = round(float(sum(score_items)), 2)
            dto.catacion_sca["puntuacion_total_sca"] = sca_total

        nueva_receta = Receta(
            dispositivo_uuid=dto.dispositivo_uuid,
            producto_id=dto.producto_id,
            nombre_receta=dto.nombre_receta,
            metodo=dto.metodo,
            dosis_cafe_g=dto.dosis_cafe_g,
            agua_ml=dto.agua_ml,
            ratio=ratio_calculado,
            molino_usado=dto.molino_usado,
            grosor_molienda=dto.grosor_molienda,
            temperatura_c=dto.temperatura_c,
            tiempo_total_s=dto.tiempo_total_s,
            calificacion_1_10=dto.calificacion_1_10,
            reintentar=dto.reintentar,
            notas_catado=dto.notas_catado,
            catacion_sca=dto.catacion_sca,
            puntuacion_sca_total=sca_total,
        )
        self.session.add(nueva_receta)
        self.session.commit()
        self.session.refresh(nueva_receta)
        return nueva_receta

