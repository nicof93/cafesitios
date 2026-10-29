import unittest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from plataforma_backend import app
from db.database import (
    Base,
    DatabaseManager,
    HistorialPrecio,
    Producto,
    Tienda,
    Variante,
)
from core.storage_manager import calcular_reporte_almacenamiento_global


class TestStoreStorageAnalytics(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(cls.engine)
        cls.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=cls.engine)

        cls.mock_db = DatabaseManager(db_url="sqlite://")
        cls.mock_db.engine = cls.engine
        cls.mock_db.SessionLocal = cls.SessionLocal
        cls._orig_local = DatabaseManager._instances.get("local")
        DatabaseManager._instances["local"] = cls.mock_db

        from api.dependencies import get_db_session, require_local_admin

        def override_get_db():
            db = cls.SessionLocal()
            try:
                yield db
            finally:
                db.close()

        def override_require_admin():
            return True

        app.dependency_overrides[get_db_session] = override_get_db
        app.dependency_overrides[require_local_admin] = override_require_admin

        # Seed data
        with cls.SessionLocal() as session:
            t1 = Tienda(
                nombre="Café Cordillera",
                url_base="https://cordillera.cl",
                plataforma="shopify",
                activo=True,
                limite_almacenamiento_mb=250,
            )
            t2 = Tienda(
                nombre="Austral Roasters",
                url_base="https://austral.cl",
                plataforma="woocommerce",
                activo=True,
                limite_almacenamiento_mb=100,
            )
            session.add_all([t1, t2])
            session.commit()
            session.refresh(t1)
            session.refresh(t2)

            p1 = Producto(
                tienda_id=t1.id,
                id_externo="PROD-1",
                nombre="Geisha Especial",
                url_detalle="https://cordillera.cl/geisha",
            )
            session.add(p1)
            session.commit()
            session.refresh(p1)

            v1 = Variante(
                producto_id=p1.id,
                id_variante_externo="VAR-1",
                opcion="250g Grano Entero",
                formato_gramos=250,
                precio_clp=14990,
                precio_original_clp=14990,
                precio_por_kilo=59960.0,
            )
            session.add(v1)
            session.commit()
            session.refresh(v1)

            h1 = HistorialPrecio(
                variante_id=v1.id,
                precio_clp=14990,
                precio_original_clp=14990,
                precio_por_kilo=59960.0,
            )
            session.add(h1)
            session.commit()

    @classmethod
    def tearDownClass(cls):
        app.dependency_overrides.clear()
        if cls._orig_local is not None:
            DatabaseManager._instances["local"] = cls._orig_local
        else:
            DatabaseManager._instances.pop("local", None)
        cls.engine.dispose()

    def setUp(self):
        self.client = TestClient(app)

    def test_calcular_reporte_almacenamiento_global_unit(self):
        with self.SessionLocal() as session:
            reporte = calcular_reporte_almacenamiento_global(session)

            self.assertIn("resumen_global", reporte)
            self.assertIn("tiendas", reporte)

            resumen = reporte["resumen_global"]
            self.assertEqual(resumen["total_tiendas"], 2)
            self.assertGreaterEqual(resumen["total_filas_bd"], 1)

            tiendas = {t["nombre"]: t for t in reporte["tiendas"]}
            self.assertIn("Café Cordillera", tiendas)
            self.assertIn("Austral Roasters", tiendas)

            cordillera = tiendas["Café Cordillera"]
            self.assertEqual(cordillera["limite_almacenamiento_mb"], 250)
            self.assertIn("imagenes", cordillera)
            self.assertIn("base_datos", cordillera)

            # Verificar desglose de base de datos
            bd = cordillera["base_datos"]
            self.assertGreaterEqual(bd["total_filas"], 1)
            self.assertGreater(bd["peso_bytes"], 0)
            self.assertIn("productos", bd["desglose_tablas"])
            self.assertEqual(bd["desglose_tablas"]["productos"]["filas"], 1)

    def test_endpoint_storage_report_canonical(self):
        response = self.client.get(
            "/api/v1/administracion/tiendas/almacenamiento",
            headers={"Host": "localhost:8000"},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("resumen_global", data)
        self.assertIn("tiendas", data)
        self.assertEqual(data["resumen_global"]["total_tiendas"], 2)

    def test_endpoint_storage_report_alias(self):
        response = self.client.get(
            "/api/v1/admin/stores/storage-report",
            headers={"Host": "localhost:8000"},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["resumen_global"]["total_tiendas"], 2)
