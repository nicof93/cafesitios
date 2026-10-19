import sys
from pathlib import Path
import unittest
from datetime import datetime, timezone
from urllib.parse import parse_qs, urlparse

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from main import app
from api.dependencies import get_db_session
from db.database import (
    Base,
    EstadoSincronizacion,
    HistorialPrecio,
    OfertaTienda,
    Producto,
    Sincronizacion,
    SincronizacionLog,
    Tienda,
    Variante,
)
from infrastructure.driving.api import (
    get_current_sync_summary,
    get_market_analytics,
    get_sync_history,
)

try:
    from fastapi.testclient import TestClient as _FastAPITestClient
except RuntimeError:
    _FastAPITestClient = None


class _DirectSyncClient:
    def __init__(self, session_factory):
        self._session_factory = session_factory

    def get(self, url: str):
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        session = self._session_factory()
        try:
            if parsed.path.endswith("/resumen-actual"):
                model = get_current_sync_summary(session)
            elif parsed.path.endswith("/historial"):
                page = int(params.get("page", ["1"])[0])
                page_size = int(params.get("page_size", ["20"])[0])
                model = get_sync_history(page=page, page_size=page_size, db_session=session)
            elif parsed.path.endswith("/mercado"):
                model = get_market_analytics(session)
            else:
                raise ValueError(f"Unsupported test path: {parsed.path}")
            payload = model.model_dump(mode="json")

            class _Resp:
                status_code = 200
                def json(self):
                    return payload

            return _Resp()
        finally:
            session.close()


class TestSyncAnalyticsAPI(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)
        self._prev_overrides = dict(app.dependency_overrides)

        def _override_get_db():
            session = self.SessionLocal()
            try:
                yield session
            finally:
                session.close()

        app.dependency_overrides[get_db_session] = _override_get_db
        self.client = _FastAPITestClient(app) if _FastAPITestClient is not None else _DirectSyncClient(self.SessionLocal)

    def tearDown(self):
        app.dependency_overrides = self._prev_overrides
        self.engine.dispose()

    def test_empty_database_returns_200_and_valid_zero_metrics(self):
        res_summary = self.client.get("/api/sincronizaciones/resumen-actual")
        self.assertEqual(res_summary.status_code, 200)
        summary = res_summary.json()
        self.assertEqual(summary["total_nuevos"], 0)
        self.assertEqual(summary["total_subieron_precio"], 0)
        self.assertEqual(summary["total_bajaron_precio"], 0)
        self.assertEqual(summary["porcentaje_variacion_global"], 0.0)
        self.assertEqual(summary["productos_nuevos"], [])
        self.assertEqual(summary["cambios_precio"], [])

        res_history = self.client.get("/api/sincronizaciones/historial")
        self.assertEqual(res_history.status_code, 200)
        history = res_history.json()
        self.assertEqual(history["total_items"], 0)
        self.assertEqual(history["items"], [])

        res_market = self.client.get("/api/analitica/mercado")
        self.assertEqual(res_market.status_code, 200)
        market = res_market.json()
        self.assertEqual(market["precio_promedio_kilo"], 0.0)
        self.assertEqual(market["total_variantes_analizadas"], 0)
        self.assertEqual(market["distribucion_tueste"], [])
        self.assertEqual(market["distribucion_proceso"], [])

    def test_resumen_actual_with_price_increases_decreases_and_new_products(self):
        session = self.SessionLocal()
        try:
            store1 = Tienda(nombre="Singular Coffee", url_base="https://singular.cl", activo=True)
            store2 = Tienda(nombre="Café Triciclo", url_base="https://triciclo.cl", activo=True)
            session.add_all([store1, store2])
            session.flush()

            # Producto 1: Bajó de precio (12000 -> 9600 CLP, -20%)
            prod_bajo = Producto(
                tienda_id=store1.id,
                nombre="Etiopía Guji Natural",
                url_detalle="https://singular.cl/guji",
                pais_origen="Etiopía",
                proceso="Natural",
                tueste="Filtro Claro",
                activo=True,
                fecha_creacion=datetime(2026, 10, 10, 10, 0),
                fecha_actualizacion=datetime(2026, 10, 16, 3, 30),
            )
            # Producto 2: Subió de precio (10000 -> 11500 CLP, +15%)
            prod_subio = Producto(
                tienda_id=store2.id,
                nombre="Colombia Huila Lavado",
                url_detalle="https://triciclo.cl/huila",
                pais_origen="Colombia",
                proceso="Lavado",
                tueste="Medio",
                activo=True,
                fecha_creacion=datetime(2026, 10, 10, 10, 0),
                fecha_actualizacion=datetime(2026, 10, 16, 3, 30),
            )
            # Producto 3: Nuevo en la última corrida (1 solo historial)
            prod_nuevo = Producto(
                tienda_id=store1.id,
                nombre="Panamá Geisha Volcán",
                url_detalle="https://singular.cl/geisha",
                pais_origen="Panamá",
                proceso="Honey",
                tueste="Claro",
                activo=True,
                fecha_creacion=datetime(2026, 10, 16, 3, 30),
                fecha_actualizacion=datetime(2026, 10, 16, 3, 30),
            )
            session.add_all([prod_bajo, prod_subio, prod_nuevo])
            session.flush()

            var_bajo = Variante(
                producto_id=prod_bajo.id,
                id_variante_externo="var-guji-250",
                opcion="250g Grano",
                formato_gramos=250,
                precio_clp=9600,
                precio_original_clp=12000,
                en_oferta=True,
                descuento_porcentaje=20,
                precio_por_kilo=38400.0,
                disponible=True,
            )
            var_subio = Variante(
                producto_id=prod_subio.id,
                id_variante_externo="var-huila-250",
                opcion="250g Grano",
                formato_gramos=250,
                precio_clp=11500,
                precio_original_clp=11500,
                en_oferta=False,
                descuento_porcentaje=0,
                precio_por_kilo=46000.0,
                disponible=True,
            )
            var_nuevo = Variante(
                producto_id=prod_nuevo.id,
                id_variante_externo="var-geisha-250",
                opcion="250g Grano",
                formato_gramos=250,
                precio_clp=18000,
                precio_original_clp=18000,
                en_oferta=False,
                descuento_porcentaje=0,
                precio_por_kilo=72000.0,
                disponible=True,
            )
            session.add_all([var_bajo, var_subio, var_nuevo])
            session.flush()

            session.add_all([
                HistorialPrecio(
                    variante_id=var_bajo.id,
                    precio_clp=12000,
                    precio_original_clp=12000,
                    precio_por_kilo=48000.0,
                    fecha_registro=datetime(2026, 10, 15, 3, 30),
                ),
                HistorialPrecio(
                    variante_id=var_bajo.id,
                    precio_clp=9600,
                    precio_original_clp=12000,
                    precio_por_kilo=38400.0,
                    en_oferta=True,
                    descuento_porcentaje=20,
                    fecha_registro=datetime(2026, 10, 16, 3, 30),
                ),
                HistorialPrecio(
                    variante_id=var_subio.id,
                    precio_clp=10000,
                    precio_original_clp=10000,
                    precio_por_kilo=40000.0,
                    fecha_registro=datetime(2026, 10, 15, 3, 30),
                ),
                HistorialPrecio(
                    variante_id=var_subio.id,
                    precio_clp=11500,
                    precio_original_clp=11500,
                    precio_por_kilo=46000.0,
                    fecha_registro=datetime(2026, 10, 16, 3, 30),
                ),
                HistorialPrecio(
                    variante_id=var_nuevo.id,
                    precio_clp=18000,
                    precio_original_clp=18000,
                    precio_por_kilo=72000.0,
                    fecha_registro=datetime(2026, 10, 16, 3, 30),
                ),
            ])

            session.add(
                SincronizacionLog(
                    fecha_ejecucion=datetime(2026, 10, 16, 3, 30, tzinfo=timezone.utc),
                    estado="OK",
                    productos_nuevos=1,
                    productos_actualizados=2,
                    productos_con_cambio_precio=2,
                    duracion_segundos=14.5,
                )
            )
            session.commit()
        finally:
            session.close()

        response = self.client.get("/api/sincronizaciones/resumen-actual")
        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertEqual(data["estado"], "OK")
        self.assertIsNotNone(data["fecha_ultima_sincronizacion"])
        self.assertEqual(data["total_nuevos"], 1)
        self.assertEqual(data["total_subieron_precio"], 1)
        self.assertEqual(data["total_bajaron_precio"], 1)
        self.assertEqual(data["total_ofertas_monitoreadas"], 3)
        self.assertEqual(data["ahorro_total_clp"], 2400)
        self.assertEqual(data["porcentaje_variacion_global"], -2.5)

        self.assertEqual(len(data["productos_nuevos"]), 1)
        self.assertEqual(data["productos_nuevos"][0]["nombre"], "Panamá Geisha Volcán")
        self.assertEqual(data["productos_nuevos"][0]["tienda"], "Singular Coffee")

        self.assertEqual(len(data["cambios_precio"]), 2)
        bajada = next(c for c in data["cambios_precio"] if c["tipo_cambio"] == "BAJO")
        subida = next(c for c in data["cambios_precio"] if c["tipo_cambio"] == "SUBIO")

        self.assertEqual(bajada["nombre"], "Etiopía Guji Natural")
        self.assertEqual(bajada["precio_anterior"], 12000)
        self.assertEqual(bajada["precio_nuevo"], 9600)
        self.assertEqual(bajada["diferencia_clp"], -2400)
        self.assertEqual(bajada["porcentaje_variacion"], -20.0)

        self.assertEqual(subida["nombre"], "Colombia Huila Lavado")
        self.assertEqual(subida["precio_anterior"], 10000)
        self.assertEqual(subida["precio_nuevo"], 11500)
        self.assertEqual(subida["diferencia_clp"], 1500)
        self.assertEqual(subida["porcentaje_variacion"], 15.0)

    def test_resumen_actual_without_price_changes(self):
        session = self.SessionLocal()
        try:
            store = Tienda(nombre="Tienda Estable", url_base="https://estable.cl", activo=True)
            session.add(store)
            session.flush()

            prod = Producto(
                tienda_id=store.id,
                nombre="Brasil Cerrado",
                url_detalle="https://estable.cl/brasil",
                activo=True,
            )
            session.add(prod)
            session.flush()

            var = Variante(
                producto_id=prod.id,
                id_variante_externo="var-brasil-250",
                opcion="250g",
                formato_gramos=250,
                precio_clp=10000,
                precio_original_clp=10000,
                precio_por_kilo=40000.0,
                disponible=True,
            )
            session.add(var)
            session.flush()

            session.add_all([
                HistorialPrecio(
                    variante_id=var.id,
                    precio_clp=10000,
                    precio_original_clp=10000,
                    precio_por_kilo=40000.0,
                    fecha_registro=datetime(2026, 10, 15, 3, 30),
                ),
                HistorialPrecio(
                    variante_id=var.id,
                    precio_clp=10000,
                    precio_original_clp=10000,
                    precio_por_kilo=40000.0,
                    fecha_registro=datetime(2026, 10, 16, 3, 30),
                ),
            ])
            session.add(
                SincronizacionLog(
                    fecha_ejecucion=datetime(2026, 10, 16, 3, 30, tzinfo=timezone.utc),
                    estado="OK",
                    productos_nuevos=0,
                    productos_actualizados=1,
                    productos_con_cambio_precio=0,
                    duracion_segundos=8.2,
                )
            )
            session.commit()
        finally:
            session.close()

        response = self.client.get("/api/sincronizaciones/resumen-actual")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["total_nuevos"], 0)
        self.assertEqual(data["total_subieron_precio"], 0)
        self.assertEqual(data["total_bajaron_precio"], 0)
        self.assertEqual(data["porcentaje_variacion_global"], 0.0)
        self.assertEqual(data["cambios_precio"], [])
        self.assertEqual(data["productos_nuevos"], [])

    def test_historial_endpoint_pagination_and_market_analytics(self):
        session = self.SessionLocal()
        try:
            store1 = Tienda(nombre="Tostaduría Sur", url_base="https://sur.cl", activo=True)
            store2 = Tienda(nombre="Tostaduría Norte", url_base="https://norte.cl", activo=True)
            session.add_all([store1, store2])
            session.flush()

            p1 = Producto(
                tienda_id=store1.id,
                nombre="Perú Cajamarca Lavado",
                url_detalle="https://sur.cl/peru",
                proceso="Lavado",
                tueste="Medio",
                activo=True,
            )
            p2 = Producto(
                tienda_id=store2.id,
                nombre="Kenia AA Natural",
                url_detalle="https://norte.cl/kenia",
                proceso="Natural",
                tueste="Filtro Claro",
                activo=True,
            )
            session.add_all([p1, p2])
            session.flush()

            session.add_all([
                Variante(
                    producto_id=p1.id,
                    id_variante_externo="sur-1",
                    opcion="250g",
                    formato_gramos=250,
                    precio_clp=9000,
                    precio_original_clp=12000,
                    en_oferta=True,
                    descuento_porcentaje=25,
                    precio_por_kilo=36000.0,
                    disponible=True,
                ),
                Variante(
                    producto_id=p2.id,
                    id_variante_externo="norte-1",
                    opcion="250g",
                    formato_gramos=250,
                    precio_clp=11000,
                    precio_original_clp=11000,
                    en_oferta=False,
                    descuento_porcentaje=0,
                    precio_por_kilo=44000.0,
                    disponible=True,
                ),
            ])

            for idx in range(3):
                session.add(
                    SincronizacionLog(
                        fecha_ejecucion=datetime(2026, 10, 14 + idx, 3, 30, tzinfo=timezone.utc),
                        estado="OK" if idx < 2 else "ERROR",
                        productos_nuevos=idx + 1,
                        productos_actualizados=10 + idx,
                        productos_con_cambio_precio=idx,
                        duracion_segundos=12.3 + idx,
                        mensaje_error=None if idx < 2 else "Timeout en tienda externa",
                    )
                )
            session.commit()
        finally:
            session.close()

        res_hist = self.client.get("/api/sincronizaciones/historial?page=1&page_size=2")
        self.assertEqual(res_hist.status_code, 200)
        hist = res_hist.json()
        self.assertEqual(hist["total_items"], 3)
        self.assertEqual(hist["total_pages"], 2)
        self.assertEqual(len(hist["items"]), 2)
        self.assertEqual(hist["items"][0]["estado"], "ERROR")
        self.assertEqual(hist["items"][0]["mensaje_error"], "Timeout en tienda externa")
        self.assertEqual(hist["items"][1]["estado"], "OK")

        res_market = self.client.get("/api/analitica/mercado")
        self.assertEqual(res_market.status_code, 200)
        market = res_market.json()
        self.assertEqual(market["precio_promedio_kilo"], 40000.0)
        self.assertEqual(market["precio_minimo_kilo"], 36000.0)
        self.assertEqual(market["precio_maximo_kilo"], 44000.0)
        self.assertEqual(market["total_tiendas_activas"], 2)
        self.assertEqual(market["tienda_mejor_descuento"]["nombre"], "Tostaduría Sur")
        self.assertEqual(market["tienda_mejor_descuento"]["descuento_promedio_porcentaje"], 25.0)
        self.assertEqual(len(market["distribucion_tueste"]), 2)
        self.assertEqual(len(market["distribucion_proceso"]), 2)

        # Verificar que infrastructure.driving.api expone los controladores
        self.assertTrue(callable(get_current_sync_summary))
        self.assertTrue(callable(get_sync_history))
        self.assertTrue(callable(get_market_analytics))


if __name__ == "__main__":
    unittest.main()
