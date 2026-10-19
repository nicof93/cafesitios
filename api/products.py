import re
from html import escape
from html.parser import HTMLParser
from typing import Any, Dict, List, Literal, Optional, Union
from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload, selectinload

from api.dependencies import get_db_session
from api.schemas import (
    CheapestProductResponse,
    PaginatedProductsResponse,
    ProductDetailResponse,
    VariantResponse,
    CompareResponse,
    CompareProductItem,
    CompareVariantItem,
    ProductMatchesResponse,
    ProductMatchItem,
    ProductRecipeResponse,
    RecommendationResponse,
    RecommendationItem,
    WeeklyPriceDropsResponse,
    WeeklyPriceDropItem,
)
from api.stores import extract_official_website
from application.get_cheapest_products import GetCheapestProductsUseCase
from application.compare_products import CompareProductsUseCase
from application.recommend_products import RecommendProductsUseCase
from application.get_weekly_price_drops import GetWeeklyPriceDropsUseCase
from db.database import Producto, ProductoNotaCata, Receta, Tienda, Variante
from infrastructure.postgres_repository import PostgresCoffeeRepository

router = APIRouter(prefix="/api/v1/products", tags=["Productos"])
productos_router = APIRouter(prefix="/api/v1/productos", tags=["Productos"])
ofertas_router = APIRouter(prefix="/api/productos", tags=["Ofertas"])

_DESCRIPTION_TAGS = {
    'a', 'b', 'blockquote', 'br', 'caption', 'div', 'em', 'figcaption', 'figure',
    'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'hr', 'i', 'img', 'li', 'ol', 'p',
    'span', 'strong', 'table', 'tbody', 'td', 'th', 'thead', 'tr', 'u', 'ul',
}
_DESCRIPTION_VOID_TAGS = {'br', 'hr', 'img'}
_DESCRIPTION_DROP_TAGS = {'embed', 'iframe', 'math', 'object', 'script', 'style', 'svg'}


def _safe_description_url(value: str) -> Optional[str]:
    value = value.strip()
    parsed = urlsplit(value)
    if parsed.scheme.lower() in {'http', 'https', 'mailto'}:
        return value
    if parsed.scheme or value.startswith(('//', '\\\\')):
        return None
    return value


def _safe_description_style(value: str) -> str:
    declarations = []
    for declaration in value.split(';'):
        name, separator, setting = declaration.partition(':')
        if not separator:
            continue
        name = name.strip().lower()
        setting = setting.strip().lower()
        if name == 'text-align' and setting in {'left', 'right', 'center', 'justify'}:
            declarations.append(f'{name}: {setting}')
        elif name == 'font-weight' and setting in {'normal', 'bold', '400', '500', '600', '700', '800', '900'}:
            declarations.append(f'{name}: {setting}')
        elif name == 'font-style' and setting in {'normal', 'italic', 'oblique'}:
            declarations.append(f'{name}: {setting}')
        elif name == 'text-decoration' and setting in {'none', 'underline', 'line-through'}:
            declarations.append(f'{name}: {setting}')
        elif name == 'color' and re.fullmatch(r'#[0-9a-f]{3,8}|[a-z]{3,20}', setting):
            declarations.append(f'{name}: {setting}')
    return '; '.join(declarations)


class _DescriptionSanitizer(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.output = []
        self.open_tags = []
        self.suppressed_depth = 0

    def handle_starttag(self, tag, attrs):
        if self.suppressed_depth:
            if tag in _DESCRIPTION_DROP_TAGS:
                self.suppressed_depth += 1
            return
        if tag in _DESCRIPTION_DROP_TAGS:
            self.suppressed_depth = 1
            return
        if tag not in _DESCRIPTION_TAGS:
            return

        safe_attrs = []
        attrs = dict(attrs)
        if tag == 'a' and attrs.get('href'):
            href = _safe_description_url(attrs['href'])
            if href:
                safe_attrs.extend([('href', href), ('rel', 'noopener noreferrer')])
                if attrs.get('title'):
                    safe_attrs.append(('title', attrs['title']))
        elif tag == 'img':
            src = _safe_description_url(attrs.get('src', ''))
            if not src:
                return
            safe_attrs.append(('src', src))
            for name in ('alt', 'title'):
                if attrs.get(name):
                    safe_attrs.append((name, attrs[name]))
        if attrs.get('style'):
            style = _safe_description_style(attrs['style'])
            if style:
                safe_attrs.append(('style', style))

        rendered_attrs = ''.join(f' {name}="{escape(value, quote=True)}"' for name, value in safe_attrs)
        self.output.append(f'<{tag}{rendered_attrs}>')
        if tag not in _DESCRIPTION_VOID_TAGS:
            self.open_tags.append(tag)

    def handle_endtag(self, tag):
        if self.suppressed_depth:
            if tag in _DESCRIPTION_DROP_TAGS:
                self.suppressed_depth -= 1
            return
        if tag not in self.open_tags:
            return
        position = len(self.open_tags) - 1 - self.open_tags[::-1].index(tag)
        for open_tag in reversed(self.open_tags[position:]):
            self.output.append(f'</{open_tag}>')
        del self.open_tags[position:]

    def handle_data(self, data):
        if not self.suppressed_depth:
            self.output.append(escape(data))

    def handle_comment(self, data):
        pass

    def get_html(self, source: Optional[str]) -> str:
        self.feed(source or '')
        self.close()
        for tag in reversed(self.open_tags):
            self.output.append(f'</{tag}>')
        self.open_tags.clear()
        return ''.join(self.output)


from core.normalizer import is_valid_tasting_note
from scrapper.coffee_metadata import generar_resumen_corto


@productos_router.get(
    "/comparar",
    response_model=CompareResponse,
    status_code=status.HTTP_200_OK,
    summary="Comparativa directa side-by-side de productos",
    description="Permite comparar hasta 4 productos con atributos técnicos, notas y perfil organoléptico."
)
@productos_router.get("/compare", response_model=CompareResponse, include_in_schema=False)
@router.get(
    "/comparar",
    response_model=CompareResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False
)
@router.get(
    "/compare",
    response_model=CompareResponse,
    status_code=status.HTTP_200_OK,
    summary="Comparativa directa side-by-side de productos",
    description="Permite comparar hasta 4 productos con atributos técnicos, notas y perfil organoléptico."
)
def compare_products(
    ids: str = Query(..., description="IDs de productos separados por coma (ej. '1,2,3')"),
    db_session: Session = Depends(get_db_session)
) -> CompareResponse:
    try:
        product_ids = [int(i.strip()) for i in ids.split(",") if i.strip().isdigit()]
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Parámetro 'ids' inválido. Debe contener IDs numéricos separados por comas."
        )

    if not product_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Debe proporcionar al menos un ID de producto."
        )

    use_case = CompareProductsUseCase(session=db_session)
    items = use_case.execute(product_ids)

    return CompareResponse(
        productos=[
            CompareProductItem(
                id=item.id,
                nombre=item.nombre,
                tienda=item.tienda,
                tienda_url=extract_official_website(item.tienda_url) or item.tienda_url,
                tienda_sitio_oficial=extract_official_website(item.tienda_url),
                tienda_catalogo_url=item.tienda_url,
                url_detalle=item.url_detalle,
                imagen=item.imagen,
                proceso=item.proceso,
                pais_origen=item.pais_origen,
                finca=item.finca,
                variedad=item.variedad,
                tueste=item.tueste,
                escala_agtron=item.escala_agtron,
                elevacion_min_msnm=item.elevacion_min_msnm,
                elevacion_max_msnm=item.elevacion_max_msnm,
                altura_msnm=item.altura_msnm,
                puntuacion_sca=item.puntuacion_sca,
                atributos_organolepticos=item.atributos_organolepticos,
                notas_cata=item.notas_cata,
                variantes_por_gramaje=[
                    CompareVariantItem(
                        id_externo=v.id_externo,
                        formato_gramos=v.formato_gramos,
                        opcion_resumida=v.opcion_resumida,
                        precio_clp=v.precio_clp,
                        precio_original_clp=v.precio_original_clp,
                        precio_por_kilo=v.precio_por_kilo,
                        en_oferta=v.en_oferta,
                        descuento_porcentaje=v.descuento_porcentaje,
                        es_estimado=v.es_estimado,
                        disponible=v.disponible,
                    )
                    for v in item.variantes_por_gramaje
                ],
            )
            for item in items
        ]
    )


@productos_router.get(
    "/recomendar",
    response_model=RecommendationResponse,
    status_code=status.HTTP_200_OK,
    summary="Recomendador interactivo por perfil de taza / Quiz (CU-07)",
    description="Calcula afinidad de cafés según método de extracción, perfil de sabor, acidez y tueste."
)
@productos_router.get("/recommend", response_model=RecommendationResponse, include_in_schema=False)
@router.get(
    "/recomendar",
    response_model=RecommendationResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False
)
@router.get(
    "/recommend",
    response_model=RecommendationResponse,
    status_code=status.HTTP_200_OK,
    summary="Recomendador interactivo por perfil de taza / Quiz (CU-07)",
    description="Calcula afinidad de cafés según método de extracción, perfil de sabor, acidez y tueste."
)
def recommend_products(
    metodo: Optional[str] = Query(None, description="Método (Espresso, Filtrado, Prensa Francesa, Cold Brew)"),
    perfil_sabor: Optional[str] = Query(None, description="Perfil de sabor (Frutal/Floral, Chocolate/Nueces, Cítrico/Balanceado, Especiado/Intenso)"),
    perfil: Optional[str] = Query(None, description="Alias de perfil de sabor del Quiz"),
    acidez: Optional[str] = Query(None, description="Preferencia de acidez (baja, media, alta)"),
    tueste: Optional[str] = Query(None, description="Nivel de tueste (Claro, Medio, Oscuro)"),
    limit: int = Query(6, ge=1, le=20, description="Cantidad máxima de recomendaciones"),
    db_session: Session = Depends(get_db_session)
) -> RecommendationResponse:
    use_case = RecommendProductsUseCase(session=db_session)
    results = use_case.execute(
        metodo=metodo,
        perfil_sabor=perfil_sabor or perfil,
        tueste=tueste,
        acidez=acidez,
        limit=limit,
    )
    return RecommendationResponse(
        recomendaciones=[
            RecommendationItem(
                id=r.id,
                nombre=r.nombre,
                tienda=r.tienda,
                url_detalle=r.url_detalle,
                imagen=r.imagen,
                proceso=r.proceso,
                pais_origen=r.pais_origen,
                variedad=r.variedad,
                tueste=r.tueste,
                precio_clp=r.precio_clp,
                precio_por_kilo=r.precio_por_kilo,
                formato_gramos=r.formato_gramos,
                es_estimado=r.es_estimado,
                disponible=r.disponible,
                puntaje_coincidencia=r.puntaje_coincidencia,
                match_score=round(min(0.99, max(0.55, r.puntaje_coincidencia / 100.0)), 2),
                motivo_recomendacion=r.motivo_recomendacion,
                notas_cata=r.notas_cata,
                variante={
                    "formato_gramos": r.formato_gramos,
                    "precio_clp": r.precio_clp,
                    "precio_por_kilo": r.precio_por_kilo,
                    "disponible": r.disponible,
                    "es_estimado": r.es_estimado,
                },
            )
            for r in results
        ]
    )


@productos_router.get(
    "/{product_id}/detalle",
    response_model=ProductDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Obtener el detalle de un producto y todas sus variantes",
    description="Retorna la ficha técnica detallada del café, notas de cata y el historial de precios por variante."
)
@productos_router.get("/{product_id}/detail", response_model=ProductDetailResponse, include_in_schema=False)
@router.get(
    "/{product_id}/detalle",
    response_model=ProductDetailResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False
)
@router.get(
    "/{product_id}/detail",
    response_model=ProductDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Obtener el detalle de un producto y todas sus variantes",
    description="Retorna la ficha técnica detallada del café, notas de cata y el historial de precios por variante."
)
def get_product_detail(product_id: int, db_session: Session = Depends(get_db_session)) -> Dict[str, Any]:
    product = (
        db_session.query(Producto)
        .join(Tienda, Producto.tienda_id == Tienda.id)
        .options(
            joinedload(Producto.tienda),
            selectinload(Producto.variantes).selectinload(Variante.historial_precios),
            selectinload(Producto.notas_cata).joinedload(ProductoNotaCata.nota),
        )
        .filter(
            Producto.id == product_id,
            Producto.activo.is_(True),
            Producto.oculto_catalogo.is_(False),
            Tienda.activo.is_(True),
        )
        .first()
    )
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Producto no encontrado"
        )

    caract = product.caracteristicas_fuente or {}
    puntuacion_sca = caract.get("puntuacion_sca") if isinstance(caract, dict) else None
    escala_agtron = caract.get("escala_agtron") if isinstance(caract, dict) else None

    if puntuacion_sca is None:
        match_sca = re.search(
            r"\b([89]\d(?:\.\d{1,2})?)\s*(?:puntos|pts|ptos|sca)\b|\bsca\s*[:|–—-]?\s*([89]\d(?:\.\d{1,2})?)\b",
            f"{product.nombre} {product.descripcion or ''}",
            re.IGNORECASE,
        )
        if match_sca:
            try:
                score_f = float(match_sca.group(1) or match_sca.group(2))
                if 80.0 <= score_f <= 99.5:
                    puntuacion_sca = round(score_f, 2)
            except (ValueError, TypeError):
                pass

    if escala_agtron is None:
        match_agtron = re.search(
            r"agtron\s*[:|–—-]?\s*(?:#\s*)?(\d{2,3})",
            f"{product.tueste or ''} {product.descripcion or ''}",
            re.IGNORECASE,
        )
        if match_agtron:
            try:
                escala_agtron = int(match_agtron.group(1))
            except (ValueError, TypeError):
                pass

    texto_completo = f"{product.nombre} {product.descripcion or ''}"
    pais_origen = product.pais_origen
    if not pais_origen:
        for pais, pat in [
            ("Colombia", r"\bcolombia(?:no)?\b"),
            ("Etiopía", r"\b(?:etiop[ií]a|ethiopia)\b"),
            ("Brasil", r"\b(?:brasil|brazil)\b"),
            ("Guatemala", r"\bguatemala\b"),
            ("Kenia", r"\b(?:kenia|kenya)\b"),
            ("Costa Rica", r"\bcosta\s+rica\b"),
            ("Panamá", r"\b(?:panam[aá]|panama)\b"),
            ("Perú", r"\b(?:per[uú]|peru)\b"),
            ("Honduras", r"\bhonduras\b"),
            ("El Salvador", r"\bel\s+salvador\b"),
            ("Nicaragua", r"\bnicaragua\b"),
            ("Ruanda", r"\b(?:ruanda|rwanda)\b"),
            ("Burundi", r"\bburundi\b"),
            ("Ecuador", r"\becuador\b"),
            ("México", r"\b(?:m[eé]xico|mexico)\b"),
            ("Bolivia", r"\bbolivia\b"),
            ("Indonesia", r"\bindonesia\b"),
        ]:
            if re.search(pat, texto_completo, re.I):
                pais_origen = pais
                break

    proceso = product.proceso
    if not proceso:
        for proc, pat in [
            ("Natural Anaeróbico", r"\b(?:natural\s+anaer[oó]bico|anaer[oó]bico\s+natural)\b"),
            ("Anaeróbico", r"\banaer[oó]bic[oa]\b"),
            ("Maceración Carbónica", r"\bmaceraci[oó]n\s+carb[oó]nica\b"),
            ("Doble Fermentación", r"\bdoble\s+fermentaci[oó]n\b"),
            ("Honey", r"\b(?:yellow|red|black|white)?\s*honey\b"),
            ("Lavado", r"\b(?:lavado|washed)\b"),
            ("Natural", r"\bnatural\b"),
        ]:
            if re.search(pat, texto_completo, re.I):
                proceso = proc
                break

    variedad = product.variedad
    if not variedad:
        for var, pat in [
            ("Sidra", r"\bsidra\b"),
            ("Geisha", r"\b(?:geisha|gesha)\b"),
            ("Pink Bourbon", r"\b(?:pink\s+bourbon|bourbon\s+rosado)\b"),
            ("Bourbon", r"\bbourbon\b"),
            ("Caturra", r"\bcaturra\b"),
            ("Castillo", r"\bcastillo\b"),
            ("Pacamara", r"\bpacamara\b"),
            ("Typica", r"\btypica\b"),
            ("Catuaí", r"\bcatua[ií]\b"),
            ("Tabi", r"\btabi\b"),
            ("SL28", r"\bsl\s*28\b"),
            ("SL34", r"\bsl\s*34\b"),
            ("Wush Wush", r"\bwush\s*wush\b"),
            ("Sudan Rume", r"\bsudan\s*rume\b"),
            ("Chiroso", r"\bchiroso\b"),
            ("Maragogipe", r"\bmaragogipe\b"),
            ("Java", r"\bjava\b"),
            ("Laurina", r"\blaurina\b"),
        ]:
            if re.search(pat, texto_completo, re.I):
                variedad = var
                break

    finca = product.finca
    if not finca:
        m_finca = re.search(r'\b(?:finca|hacienda)\s+([A-Za-zÀ-ÿ0-9\s]+?)(?:[-–—·•,\n]|$)', texto_completo, re.I)
        if m_finca:
            f_cand = m_finca.group(1).strip()
            if 2 <= len(f_cand) <= 40:
                finca = f_cand.title()
        elif re.search(r'\bel\s+vergel\b', texto_completo, re.I):
            finca = "El Vergel"

    tienda_nombre = (product.tienda.nombre or '').replace(')', '').strip()
    official_store_url = extract_official_website(product.tienda.url_base) or product.tienda.url_base

    caract_fuente = product.caracteristicas_fuente or {}
    resumen_corto = (
        caract_fuente.get("resumen_corto")
        if isinstance(caract_fuente, dict) else None
    )
    if not resumen_corto:
        notas_validas = [
            relation.nota.nombre
            for relation in product.notas_cata
            if relation.nota and is_valid_tasting_note(relation.nota.nombre)
        ]
        resumen_corto = generar_resumen_corto(
            titulo=product.nombre,
            descripcion=product.descripcion,
            notas=notas_validas,
            proceso=proceso,
            origen=pais_origen,
            variedad=variedad,
        )

    return {
        "id": product.id,
        "tienda": tienda_nombre,
        "tienda_id": product.tienda.id if product.tienda else None,
        "tienda_telefono_whatsapp": getattr(product.tienda, "telefono_whatsapp", None) if product.tienda else None,
        "tienda_url": official_store_url,
        "tienda_sitio_oficial": official_store_url,
        "sitio_oficial": official_store_url,
        "tienda_catalogo_url": product.tienda.url_base,
        "nombre": product.nombre,
        "descripcion": _DescriptionSanitizer().get_html(product.descripcion),
        "descripcion_resumida": resumen_corto,
        "resumen_corto": resumen_corto,
        "url_detalle": product.url_detalle,
        "imagen": product.imagen,
        "fecha_actualizacion": product.fecha_actualizacion,
        "proceso": proceso,
        "tueste": product.tueste,
        "puntuacion_sca": puntuacion_sca,
        "escala_agtron": escala_agtron,
        "pais_origen": pais_origen,
        "origen": pais_origen,
        "finca": finca,
        "variedad": variedad,
        "elevacion_min_msnm": product.elevacion_min_msnm,
        "elevacion_max_msnm": product.elevacion_max_msnm,
        "cosecha": product.cosecha,
        "fermentacion_tipo": product.fermentacion_tipo,
        "fermentacion_horas": float(product.fermentacion_horas) if product.fermentacion_horas is not None else None,
        "caracteristicas_fuente": product.caracteristicas_fuente or {},
        "notas_cata": [
            {
                "nombre": relation.nota.nombre,
                "clave_normalizada": relation.nota.clave_normalizada,
                "texto_origen": relation.texto_origen,
                "confianza": relation.confianza,
                "version_extractor": relation.version_extractor,
            }
            for relation in sorted(product.notas_cata, key=lambda relation: relation.nota.clave_normalizada)
            if relation.nota and is_valid_tasting_note(relation.nota.nombre) and is_valid_tasting_note(relation.nota.clave_normalizada)
        ],
        "variantes": [
            {
                "id_externo": variant.id_variante_externo,
                "opcion": variant.opcion,
                "formato_gramos": variant.formato_gramos,
                "precio_clp": variant.precio_clp,
                "precio_original_clp": variant.precio_original_clp,
                "en_oferta": variant.en_oferta,
                "descuento_porcentaje": variant.descuento_porcentaje,
                "precio_por_kilo": float(variant.precio_por_kilo),
                "es_estimado": bool(getattr(variant, 'es_estimado', True)),
                "disponible": variant.disponible,
                "fecha_actualizacion": variant.fecha_actualizacion,
                "historial_precios": [
                    {
                        "fecha_registro": history.fecha_registro,
                        "precio_clp": history.precio_clp,
                        "precio_por_kilo": float(history.precio_por_kilo),
                    }
                    for history in sorted(
                        variant.historial_precios,
                        key=lambda history: history.fecha_registro,
                    )
                ],
            }
            for variant in product.variantes
        ],
        "recetas": [
            {
                "id": r.id,
                "nombre_receta": r.nombre_receta,
                "metodo": r.metodo,
                "dosis_cafe_g": float(r.dosis_cafe_g),
                "agua_ml": float(r.agua_ml),
                "ratio": r.ratio,
                "molino_usado": r.molino_usado,
                "grosor_molienda": r.grosor_molienda,
                "temperatura_c": r.temperatura_c,
                "tiempo_total_s": r.tiempo_total_s,
                "notas_catado": r.notas_catado,
                "es_borrador": bool(getattr(r, "es_borrador", False)),
                "pasos": r.pasos if isinstance(r.pasos, list) else None,
                "autor_tipo": getattr(r, "autor_tipo", "tostaduria") or "tostaduria",
                "tienda_nombre": r.tienda.nombre if r.tienda else product.tienda.nombre,
                "fecha_creacion": r.fecha_creacion,
            }
            for r in (
                db_session.query(Receta)
                .options(joinedload(Receta.tienda))
                .filter(
                    Receta.producto_id == product.id,
                    Receta.es_publica.is_(True),
                    Receta.es_borrador.is_(False),
                )
                .order_by(Receta.fecha_creacion.desc())
                .all()
            )
        ],
    }


@productos_router.get(
    "/{product_id}/recetas",
    response_model=List[ProductRecipeResponse],
    status_code=status.HTTP_200_OK,
    summary="Listar recetas públicas de preparación para este café",
)
@productos_router.get("/{product_id}/recipes", response_model=List[ProductRecipeResponse], include_in_schema=False)
@router.get(
    "/{product_id}/recetas",
    response_model=List[ProductRecipeResponse],
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
@router.get(
    "/{product_id}/recipes",
    response_model=List[ProductRecipeResponse],
    status_code=status.HTTP_200_OK,
    summary="Listar recetas públicas de preparación para este café",
)
def get_product_recipes(product_id: int, db_session: Session = Depends(get_db_session)) -> List[Dict[str, Any]]:
    prod = (
        db_session.query(Producto)
        .filter(
            Producto.id == product_id,
            Producto.activo.is_(True),
            Producto.oculto_catalogo.is_(False),
        )
        .first()
    )
    if prod is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Producto no encontrado",
        )

    recetas_db = (
        db_session.query(Receta)
        .options(joinedload(Receta.tienda))
        .filter(
            Receta.producto_id == product_id,
            Receta.es_publica.is_(True),
            Receta.es_borrador.is_(False),
        )
        .order_by(Receta.fecha_creacion.desc())
        .all()
    )
    return [
        {
            "id": r.id,
            "nombre_receta": r.nombre_receta,
            "metodo": r.metodo,
            "dosis_cafe_g": float(r.dosis_cafe_g),
            "agua_ml": float(r.agua_ml),
            "ratio": r.ratio,
            "molino_usado": r.molino_usado,
            "grosor_molienda": r.grosor_molienda,
            "temperatura_c": r.temperatura_c,
            "tiempo_total_s": r.tiempo_total_s,
            "notas_catado": r.notas_catado,
            "es_borrador": bool(getattr(r, "es_borrador", False)),
            "pasos": r.pasos if isinstance(r.pasos, list) else None,
            "autor_tipo": getattr(r, "autor_tipo", "tostaduria") or "tostaduria",
            "tienda_nombre": r.tienda.nombre if r.tienda else None,
            "fecha_creacion": r.fecha_creacion,
        }
        for r in recetas_db
    ]


@productos_router.get(
    "/{product_id}/coincidencias",
    response_model=ProductMatchesResponse,
    status_code=status.HTTP_200_OK,
    summary="Comparador de disponibilidad 'Comprar con...' (CU-04)",
    description="Busca si el mismo grano se comercializa en otras tiendas bajo identidad estricta (RN-04)."
)
@productos_router.get("/{product_id}/matches", response_model=ProductMatchesResponse, include_in_schema=False)
@router.get(
    "/{product_id}/coincidencias",
    response_model=ProductMatchesResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False
)
@router.get(
    "/{product_id}/matches",
    response_model=ProductMatchesResponse,
    status_code=status.HTTP_200_OK,
    summary="Comparador de disponibilidad 'Comprar con...' (CU-04)",
    description="Busca si el mismo grano se comercializa en otras tiendas bajo identidad estricta (RN-04)."
)
def get_product_matches(product_id: int, db_session: Session = Depends(get_db_session)) -> ProductMatchesResponse:
    origin_prod = (
        db_session.query(Producto)
        .options(selectinload(Producto.variantes))
        .filter(
            Producto.id == product_id,
            Producto.activo.is_(True),
            Producto.oculto_catalogo.is_(False),
        )
        .first()
    )
    if origin_prod is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Producto no encontrado"
        )

    origin_cheapest = min(origin_prod.variantes, key=lambda v: (not v.disponible, v.precio_por_kilo)) if origin_prod.variantes else None
    origin_price = origin_cheapest.precio_clp if origin_cheapest else 0
    origin_kilo = float(origin_cheapest.precio_por_kilo) if origin_cheapest else 0.0

    repo = PostgresCoffeeRepository(session=db_session)
    matches = repo.find_matching_products(product_id)

    coincidencias = []
    for m in matches:
        var = m.variante_mas_barata
        diff_precio = var.precio_clp - origin_price
        diff_kilo = var.precio_por_kilo - origin_kilo
        coincidencias.append(
            ProductMatchItem(
                id=m.id,
                tienda=m.tienda,
                nombre=m.nombre,
                url_detalle=m.url_detalle,
                imagen=m.imagen,
                precio_clp=var.precio_clp,
                precio_por_kilo=var.precio_por_kilo,
                formato_gramos=var.formato_gramos,
                diferencia_precio_clp=diff_precio,
                diferencia_kilo_clp=round(diff_kilo, 2),
                es_mas_barato=(diff_kilo < 0),
            )
        )

    return ProductMatchesResponse(
        producto_origen_id=product_id,
        coincidencias=coincidencias
    )


@productos_router.get(
    "",
    response_model=PaginatedProductsResponse,
    status_code=status.HTTP_200_OK,
    summary="Catálogo de productos con filtros y ordenamiento",
    description="Permite buscar y ordenar los cafés aplicando filtros por formato (gramos), tienda, precio o variedad."
)
@productos_router.get(
    "/",
    response_model=PaginatedProductsResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False
)
@productos_router.get(
    "/cheapest",
    response_model=PaginatedProductsResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False
)
@router.get(
    "",
    response_model=PaginatedProductsResponse,
    status_code=status.HTTP_200_OK,
    summary="Catálogo de productos con filtros y ordenamiento",
    description="Permite buscar y ordenar los cafés aplicando filtros por formato (gramos), tienda, precio o variedad."
)
@router.get(
    "/",
    response_model=PaginatedProductsResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False
)
@router.get(
    "/cheapest",
    response_model=PaginatedProductsResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False
)
def get_cheapest_coffee_products(
    sort_by: Literal["kilo", "unit"] = Query(
        "kilo",
        description="Criterio de ordenamiento: 'kilo' ($/kg) o 'unit' (precio unitario en CLP)"
    ),
    limit: int = Query(10, ge=1, le=1000, description="Cantidad de productos a retornar (1-1000)"),
    offset: int = Query(0, ge=0, description="Desplazamiento / paginación para scroll infinito (offset)"),
    category: Optional[str] = Query("cafe", description="Filtrar por categoría: 'cafe' (predeterminado), 'no_cafe', o 'todos'"),
    only_available: bool = Query(True, description="Filtrar solo productos que tengan stock disponible"),
    store_name: Optional[List[str]] = Query(None, description="Filtrar por nombre(s) de tienda (ej. 'Singular' o múltiples)"),
    store: Optional[List[str]] = Query(None, description="Alias de tienda (ej. 'Singular')"),
    tienda: Optional[List[str]] = Query(None, description="Alias en español para tienda"),
    stores: Optional[List[str]] = Query(None, description="Múltiples tiendas separadas por coma o repetidas"),
    tiendas: Optional[List[str]] = Query(None, description="Múltiples tiendas en español"),
    min_weight_g: Optional[int] = Query(None, ge=50, le=5000, description="Peso mínimo en gramos (ej. 200)"),
    max_weight_g: Optional[int] = Query(None, ge=50, le=5000, description="Peso máximo en gramos (ej. 300)"),
    search_query: Optional[str] = Query(None, description="Búsqueda por texto en el nombre del café (ej. 'Geisha')"),
    min_price: Optional[Union[int, str]] = Query(None, description="Precio unitario mínimo en CLP"),
    max_price: Optional[Union[int, str]] = Query(None, description="Precio unitario máximo en CLP"),
    min_price_kilo: Optional[Union[int, str]] = Query(None, description="Precio por kilo mínimo en CLP"),
    max_price_kilo: Optional[Union[int, str]] = Query(None, description="Precio por kilo máximo en CLP"),
    process: Optional[str] = Query(None, max_length=255, description="Filtrar por proceso de beneficio"),
    country: Optional[str] = Query(None, max_length=255, description="Filtrar por país de origen"),
    pais_origen: Optional[str] = Query(None, max_length=255, description="Alias en español para país de origen"),
    variety: Optional[str] = Query(None, max_length=255, description="Filtrar por variedad del café"),
    variedad: Optional[str] = Query(None, max_length=255, description="Alias en español para variedad"),
    notes: Optional[str] = Query(None, max_length=255, description="Filtrar por nota de cata"),
    notas_cata: Optional[str] = Query(None, max_length=255, description="Alias en español para nota de cata"),
    tasting_notes: Optional[str] = Query(None, max_length=255, description="Alias de nota de cata"),
    db_session: Session = Depends(get_db_session)
) -> PaginatedProductsResponse:
    try:
        raw_stores: List[str] = []
        for param in (store_name, store, tienda, stores, tiendas):
            if param:
                if isinstance(param, list):
                    for item in param:
                        raw_stores.extend([s.strip() for s in item.split(",") if s.strip()])
                elif isinstance(param, str):
                    raw_stores.extend([s.strip() for s in param.split(",") if s.strip()])

        selected_stores = list(dict.fromkeys(raw_stores))
        store_filter_str = ",".join(selected_stores) if selected_stores else None

        def _to_clean_str(val: Optional[str]) -> Optional[str]:
            if val is None:
                return None
            s = str(val).strip()
            return s if s else None

        def _to_clean_int(val: Optional[Union[int, str]]) -> Optional[int]:
            if val is None:
                return None
            if isinstance(val, int):
                return val if val >= 0 else None
            s = str(val).strip()
            if not s:
                return None
            try:
                parsed = int(s)
                return parsed if parsed >= 0 else None
            except (ValueError, TypeError):
                return None

        clean_search_query = _to_clean_str(search_query)
        clean_process = _to_clean_str(process)
        clean_country = _to_clean_str(country or pais_origen)
        clean_variety = _to_clean_str(variety or variedad)
        clean_notes = _to_clean_str(notes or notas_cata or tasting_notes)
        clean_min_price = _to_clean_int(min_price)
        clean_max_price = _to_clean_int(max_price)
        clean_min_price_kilo = _to_clean_int(min_price_kilo)
        clean_max_price_kilo = _to_clean_int(max_price_kilo)

        categoria_filtro = None if category in ("todos", "all", "", None) else _to_clean_str(category)

        import api.router
        repo_cls = getattr(api.router, "PostgresCoffeeRepository", PostgresCoffeeRepository)
        repository = repo_cls(session=db_session)
        use_case = GetCheapestProductsUseCase(repository=repository)

        productos_dominio = use_case.execute(
            sort_by=sort_by,
            limit=limit,
            offset=offset,
            only_available=only_available,
            store_name=store_filter_str,
            min_weight_g=min_weight_g,
            max_weight_g=max_weight_g,
            search_query=clean_search_query,
            min_price=clean_min_price,
            max_price=clean_max_price,
            process=clean_process,
            country=clean_country,
            variety=clean_variety,
            tasting_notes=clean_notes,
            min_price_kilo=clean_min_price_kilo,
            max_price_kilo=clean_max_price_kilo,
            category=categoria_filtro,
        )

        total_items = len(productos_dominio)
        if hasattr(repository, "count_cheapest_products"):
            total_items = repository.count_cheapest_products(
                sort_by=sort_by,
                only_available=only_available,
                store_name=store_filter_str,
                min_weight_g=min_weight_g,
                max_weight_g=max_weight_g,
                search_query=clean_search_query,
                min_price=clean_min_price,
                max_price=clean_max_price,
                process=clean_process,
                country=clean_country,
                variety=clean_variety,
                tasting_notes=clean_notes,
                min_price_kilo=clean_min_price_kilo,
                max_price_kilo=clean_max_price_kilo,
                category=categoria_filtro,
            )

        items_dto = [
            CheapestProductResponse(
                id=prod.id,
                tienda=prod.tienda,
                tienda_id=getattr(prod, 'tienda_id', None),
                tienda_telefono_whatsapp=getattr(prod, 'tienda_telefono_whatsapp', None),
                nombre=prod.nombre,
                url_detalle=prod.url_detalle,
                imagen=prod.imagen,
                categoria=getattr(prod, 'categoria', 'cafe'),
                oculto_catalogo=bool(getattr(prod, 'oculto_catalogo', False)),
                variante=VariantResponse(
                    id_externo=prod.variante_mas_barata.id_externo,
                    opcion=prod.variante_mas_barata.opcion,
                    formato_gramos=prod.variante_mas_barata.formato_gramos,
                    precio_clp=prod.variante_mas_barata.precio_clp,
                    precio_original_clp=prod.variante_mas_barata.precio_original_clp,
                    en_oferta=prod.variante_mas_barata.en_oferta,
                    descuento_porcentaje=prod.variante_mas_barata.descuento_porcentaje,
                    precio_por_kilo=prod.variante_mas_barata.precio_por_kilo,
                    disponible=prod.variante_mas_barata.disponible,
                    es_estimado=prod.variante_mas_barata.es_estimado,
                )
            ) for prod in productos_dominio
        ]

        return PaginatedProductsResponse(
            total_items=total_items,
            criterio_orden=f"Precio por {'kilo ($/kg)' if sort_by == 'kilo' else 'unidad ($ CLP)'}",
            data=items_dto
        )

    except Exception as e:

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno al procesar la consulta: {str(e)}"
        )


@productos_router.get(
    "/ofertas-semana",
    response_model=WeeklyPriceDropsResponse,
    status_code=status.HTTP_200_OK,
    summary="Mayores caídas de precio de la semana (Ofertas verificadas)",
    description="Devuelve los cafés con mayores descuentos y rebajas reales verificadas en los últimos 7 días."
)
@productos_router.get(
    "/caidas-semana",
    response_model=WeeklyPriceDropsResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False
)
@router.get(
    "/ofertas-semana",
    response_model=WeeklyPriceDropsResponse,
    status_code=status.HTTP_200_OK,
    summary="Mayores caídas de precio de la semana (Ofertas verificadas)",
    description="Devuelve los cafés con mayores descuentos y rebajas reales verificadas en los últimos 7 días."
)
@router.get(
    "/caidas-semana",
    response_model=WeeklyPriceDropsResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False
)
@ofertas_router.get(
    "/ofertas-semana",
    response_model=WeeklyPriceDropsResponse,
    status_code=status.HTTP_200_OK,
    summary="Mayores caídas de precio de la semana (Ofertas verificadas)",
    description="Devuelve los cafés con mayores descuentos y rebajas reales verificadas en los últimos 7 días."
)
@ofertas_router.get(
    "/bajas-precio-semana",
    response_model=WeeklyPriceDropsResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False
)
def get_weekly_price_drops(
    limit: int = Query(10, ge=1, le=50, description="Límite máximo de ofertas a retornar"),
    dias: int = Query(7, ge=1, le=30, description="Ventana de días para evaluar la caída de precio"),
    db_session: Session = Depends(get_db_session)
) -> WeeklyPriceDropsResponse:
    use_case = GetWeeklyPriceDropsUseCase(db_session)
    items = use_case.execute(limit=limit, dias=dias)
    return WeeklyPriceDropsResponse(
        total=len(items),
        dias_evaluados=dias,
        ofertas=items
    )

