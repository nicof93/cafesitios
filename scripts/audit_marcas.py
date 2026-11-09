#!/usr/bin/env python3
"""
scripts/audit_marcas.py
-----------------------
Auditoría y salud de datos de marcas (tostadurías) y ofertas en Cafesitios.
Verifica:
1. Consistencia de dominio canónico raíz en tiendas.
2. Integridad de tienda_catalogos y prevención de duplicados en tiendas.
3. Integridad de precios ($0 CLP), gramajes (<=0 g) y $/kg anómalos.
4. Metadatos de geolocalización física y reputación.
5. Salida de reporte JSON en output/audit_marcas_report.json.
"""

import json
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

# Agregar raíz del proyecto al path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from db.database import DatabaseManager, Producto, SucursalTienda, Tienda, TiendaCatalogo, Variante
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload


def extract_clean_domain(url: Optional[str]) -> Optional[str]:
    """Extrae protocolo y netloc limpio sin rutas ni query params."""
    if not url or not str(url).strip():
        return None
    raw = str(url).strip()
    if not raw.startswith(("http://", "https://")):
        raw = f"https://{raw}"
    parsed = urlparse(raw)
    if not parsed.netloc:
        return None
    return f"{parsed.scheme.lower()}://{parsed.netloc.lower()}"


def run_brand_audit() -> Dict[str, Any]:
    db = DatabaseManager()
    session = db.SessionLocal()

    report: Dict[str, Any] = {
        "fecha_auditoria": datetime.now(timezone.utc).isoformat(),
        "resumen_ejecutivo": {},
        "marcas": [],
        "alertas_scraping": [],
        "inconsistencias_dominios": [],
        "multi_fuentes_duplicados": [],
        "metadatos_reputacion_fisica": {}
    }

    try:
        # 1. Cargar todas las tiendas con productos, variantes y catálogos
        tiendas = (
            session.query(Tienda)
            .options(
                selectinload(Tienda.productos).selectinload(Producto.variantes),
                selectinload(Tienda.catalogos),
                selectinload(Tienda.sucursales)
            )
            .order_by(Tienda.nombre.asc())
            .all()
        )

        total_tiendas = len(tiendas)
        total_tiendas_activas = sum(1 for t in tiendas if t.activo)
        total_productos_global = 0
        total_productos_activos = 0
        total_variantes_global = 0
        total_ofertas_cero = 0
        total_gramajes_invalidos = 0
        total_precios_kilo_anomalos = 0

        # Mapeo para detección de dominios duplicados entre tiendas
        dominio_a_tiendas: Dict[str, List[Dict[str, Any]]] = {}

        for t in tiendas:
            # Chequeo de URL canónica limpia
            url_original = t.url_base or ""
            clean_domain = extract_clean_domain(url_original)
            parsed_orig = urlparse(url_original if url_original.startswith(("http://", "https://")) else f"https://{url_original}")

            tiene_ruta_no_raiz = bool(parsed_orig.path and parsed_orig.path != "/" and len(parsed_orig.path.strip("/")) > 0)
            if tiene_ruta_no_raiz:
                report["inconsistencias_dominios"].append({
                    "tienda_id": t.id,
                    "nombre": t.nombre,
                    "url_actual": url_original,
                    "dominio_raiz_sugerido": clean_domain,
                    "motivo": "La URL base contiene rutas secundarias o colecciones en lugar del dominio raíz limpio."
                })

            if clean_domain:
                netloc = urlparse(clean_domain).netloc.replace("www.", "")
                dominio_a_tiendas.setdefault(netloc, []).append({
                    "id": t.id,
                    "nombre": t.nombre,
                    "url_base": t.url_base,
                    "activo": t.activo
                })

            # Analítica de productos y variantes
            prods = t.productos or []
            prods_activos = [p for p in prods if p.activo and not p.oculto_catalogo]
            prods_inactivos = [p for p in prods if not p.activo or p.oculto_catalogo]

            precios_kilo_validos: List[float] = []
            alertas_tienda: List[Dict[str, Any]] = []

            for p in prods_activos:
                total_productos_activos += 1
                for v in (p.variantes or []):
                    total_variantes_global += 1
                    precio = v.precio_clp or 0
                    gramos = v.formato_gramos or 0
                    precio_kilo = float(v.precio_por_kilo or 0.0)

                    # 1. Alerta precio $0 CLP
                    if precio <= 0:
                        total_ofertas_cero += 1
                        alertas_tienda.append({
                            "tipo": "PRECIO_CERO",
                            "producto_id": p.id,
                            "producto_nombre": p.nombre,
                            "variante_id": v.id,
                            "precio_clp": precio,
                            "url_detalle": p.url_detalle
                        })

                    # 2. Alerta formato gramos ausente o anómalo
                    if gramos <= 0:
                        total_gramajes_invalidos += 1
                        alertas_tienda.append({
                            "tipo": "GRAMAJE_INVALIDO",
                            "producto_id": p.id,
                            "producto_nombre": p.nombre,
                            "variante_id": v.id,
                            "formato_gramos": gramos,
                            "url_detalle": p.url_detalle
                        })

                    # 3. Alerta precio por kilo anómalo (< $5.000 CLP o > $250.000 CLP para café especial)
                    if precio > 0 and gramos > 0:
                        if precio_kilo < 5000 or precio_kilo > 250000:
                            total_precios_kilo_anomalos += 1
                            alertas_tienda.append({
                                "tipo": "PRECIO_KILO_ANOMALO",
                                "producto_id": p.id,
                                "producto_nombre": p.nombre,
                                "variante_id": v.id,
                                "precio_clp": precio,
                                "formato_gramos": gramos,
                                "precio_por_kilo": precio_kilo,
                                "url_detalle": p.url_detalle
                            })
                        else:
                            precios_kilo_validos.append(precio_kilo)

            total_productos_global += len(prods)
            precio_kilo_promedio = round(sum(precios_kilo_validos) / len(precios_kilo_validos), 2) if precios_kilo_validos else 0.0

            # Catálogos secundarios asociados
            catalogos_extra = [
                {"id": c.id, "url_catalogo": c.url_catalogo, "activa": c.activa, "etiqueta": c.etiqueta}
                for c in (t.catalogos or [])
            ]

            # Geolocalización y reputación física
            sucursales_list = [
                {
                    "id": s.id,
                    "nombre": s.nombre,
                    "direccion": s.direccion,
                    "comuna": s.comuna,
                    "lat": float(s.latitud) if s.latitud is not None else None,
                    "lon": float(s.longitud) if s.longitud is not None else None,
                    "activo": s.activo
                }
                for s in (t.sucursales or [])
            ]

            tiene_ubicacion_fisica = bool(
                (t.latitud is not None and t.longitud is not None) or
                any(s["lat"] is not None and s["lon"] is not None for s in sucursales_list)
            )

            # Metadata reputación (soporte Schema.org / Google Places)
            func_override = t.funcionalidades_override or {}
            google_place_id = func_override.get("google_place_id")
            rating = func_override.get("rating")
            total_resenas = func_override.get("total_resenas")

            marca_info = {
                "id": t.id,
                "nombre": t.nombre,
                "slug": t.slug or f"tienda-{t.id}",
                "url_base": t.url_base,
                "sitio_oficial": clean_domain,
                "plataforma": t.plataforma,
                "activo": t.activo,
                "es_prospecto": t.es_prospecto,
                "cantidad_productos_total": len(prods),
                "cantidad_productos_activos": len(prods_activos),
                "cantidad_productos_inactivos": len(prods_inactivos),
                "precio_kilo_promedio_clp": precio_kilo_promedio,
                "catalogos_adicionales_count": len(catalogos_extra),
                "catalogos_adicionales": catalogos_extra,
                "sucursales_count": len(sucursales_list),
                "sucursales": sucursales_list,
                "tiene_geolocalizacion": tiene_ubicacion_fisica,
                "reputacion_fisica": {
                    "google_place_id": google_place_id,
                    "rating": rating,
                    "total_resenas": total_resenas,
                    "disponible": bool(google_place_id or rating)
                },
                "total_alertas": len(alertas_tienda),
                "alertas": alertas_tienda[:5]  # Muestra máxima de 5 por marca en resumen
            }

            report["marcas"].append(marca_info)
            if alertas_tienda:
                report["alertas_scraping"].extend(alertas_tienda)

        # 2. Auditar si existen tiendas duplicadas para un mismo dominio raíz
        for dom, lista in dominio_a_tiendas.items():
            if len(lista) > 1:
                report["multi_fuentes_duplicados"].append({
                    "dominio": dom,
                    "tiendas_afectadas": lista,
                    "observacion": "Múltiples registros en tabla 'tiendas' comparten el mismo dominio raíz. Deben consolidarse vía 'tienda_catalogos'."
                })

        # 3. Resumen Ejecutivo
        tiendas_con_geo = sum(1 for m in report["marcas"] if m["tiene_geolocalizacion"])
        tiendas_con_reputacion = sum(1 for m in report["marcas"] if m["reputacion_fisica"]["disponible"])

        report["resumen_ejecutivo"] = {
            "total_marcas_registradas": total_tiendas,
            "total_marcas_activas": total_tiendas_activas,
            "total_productos_global": total_productos_global,
            "total_productos_activos": total_productos_activos,
            "total_variantes_evaluadas": total_variantes_global,
            "tiendas_con_ubicacion_geografica": tiendas_con_geo,
            "tiendas_sin_ubicacion_geografica": total_tiendas - tiendas_con_geo,
            "tiendas_con_reputacion_fisica_google": tiendas_con_reputacion,
            "anomalias_detectadas": {
                "inconsistencias_dominio_raiz": len(report["inconsistencias_dominios"]),
                "dominios_duplicados_en_tiendas": len(report["multi_fuentes_duplicados"]),
                "ofertas_con_precio_cero": total_ofertas_cero,
                "ofertas_con_gramaje_invalido": total_gramajes_invalidos,
                "ofertas_con_precio_kilo_anomalo": total_precios_kilo_anomalos
            }
        }

        # 4. Guardar archivo JSON de salida
        output_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "output", "audit_marcas_report.json"))
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        print("\n" + "="*70)
        print("  CAFESITIOS - REPORTE DE AUDITORÍA Y SALUD DE MARCAS")
        print("="*70)
        print(f" Marcas evaluadas: {total_tiendas} (Activas: {total_tiendas_activas})")
        print(f" Productos en catálogo: {total_productos_global} (Activos: {total_productos_activos})")
        print(f" Variantes evaluadas: {total_variantes_global}")
        print(f" Tiendas con GPS/Sucursal: {tiendas_con_geo} / {total_tiendas}")
        print(f" Inconsistencias de dominio raíz: {len(report['inconsistencias_dominios'])}")
        print(f" Dominios duplicados en 'tiendas': {len(report['multi_fuentes_duplicados'])}")
        print(f" Ofertas $0 CLP: {total_ofertas_cero}")
        print(f" Gramajes <= 0: {total_gramajes_invalidos}")
        print(f" $/kg Anómalos: {total_precios_kilo_anomalos}")
        print(f"\n Reporte detallado guardado en: {output_path}")
        print("="*70 + "\n")

        return report

    finally:
        session.close()


if __name__ == "__main__":
    run_brand_audit()
