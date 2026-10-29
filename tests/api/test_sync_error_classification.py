import unittest
from core.error_classifier import clasificar_error_sincronizacion
from db.database import DatabaseManager, Cafe, Tienda


class TestSyncErrorClassification(unittest.TestCase):
    def test_tienda_protegida_password_classification(self):
        err_401 = "HTTP Error 401: Unauthorized"
        diag = clasificar_error_sincronizacion(err_401)
        self.assertEqual(diag["codigo"], "TIENDA_PROTEGIDA_PASSWORD")
        self.assertIn("Contraseña", diag["categoria"])
        self.assertTrue(diag["es_error"])

        err_pass = "La tienda tiene habilitada la protección por contraseña (/password)"
        diag2 = clasificar_error_sincronizacion(err_pass)
        self.assertEqual(diag2["codigo"], "TIENDA_PROTEGIDA_PASSWORD")

    def test_sitio_caido_o_timeout_classification(self):
        err_timeout = "HTTPSConnectionPool(host='apricatcoffee.com', port=443): Read timed out. (read timeout=10)"
        diag = clasificar_error_sincronizacion(err_timeout)
        self.assertEqual(diag["codigo"], "SITIO_CAIDO_O_TIMEOUT")
        self.assertIn("Caído", diag["categoria"])

        err_dns = "Failed to resolve 'https://tiendainexistente12345.cl' (getaddrinfo failed)"
        diag_dns = clasificar_error_sincronizacion(err_dns)
        self.assertEqual(diag_dns["codigo"], "SITIO_CAIDO_O_TIMEOUT")

    def test_error_servidor_5xx(self):
        err_502 = "HTTP 502 Bad Gateway"
        diag = clasificar_error_sincronizacion(err_502)
        self.assertEqual(diag["codigo"], "ERROR_SERVIDOR_TIENDA")

    def test_catalogo_no_encontrado_404(self):
        err_404 = "HTTP Error 404: Not Found"
        diag = clasificar_error_sincronizacion(err_404)
        self.assertEqual(diag["codigo"], "CATALOGO_NO_ENCONTRADO")

    def test_rate_limit_429(self):
        err_429 = "HTTP 429 Too Many Requests"
        diag = clasificar_error_sincronizacion(err_429)
        self.assertEqual(diag["codigo"], "BLOQUEO_BOT_O_RATE_LIMIT")

    def test_error_base_datos(self):
        err_sql = "(psycopg.errors.StringDataRightTruncation) value too long for type character varying(100)"
        diag = clasificar_error_sincronizacion(err_sql)
        self.assertEqual(diag["codigo"], "ERROR_BASE_DATOS")

    def test_pickers_long_lote_persistence_without_truncation_error(self):
        """Valida que un lote largo (> 100 chars como en Pickers) no cause StringDataRightTruncation."""
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from sqlalchemy.pool import StaticPool
        from db.database import Base

        engine = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
        Base.metadata.create_all(engine)
        db = DatabaseManager(db_url="sqlite://")
        db.engine = engine
        db.SessionLocal = sessionmaker(bind=engine)

        long_lote = "Bourbon, Caturra y Catuaí— son en realidad una familia: Caturra es una mutación de Bourbon, y Catuaí es hija de Caturra"
        self.assertGreater(len(long_lote), 100)

        with db.SessionLocal() as session:
            t = Tienda(
                nombre="Test Pickers Long Lote Store",
                url_base="https://test-pickers.cl",
                plataforma="shopify",
                activo=True,
            )
            session.add(t)
            session.commit()
            session.refresh(t)
            t_id = t.id

        try:
            catalogo = [
                {
                    "nombre": "Qawale Test",
                    "origen": "Guatemala",
                    "finca_productor": "Finca San Jerónimo",
                    "variedad": "Bourbon",
                    "proceso": "Lavado",
                    "lote": long_lote,
                    "notas_cata": ["Manzana", "Caramelo"],
                    "notas_normalizadas": ["Manzana", "Caramelo"],
                    "hash_descripcion": "pickers_test_hash_123",
                    "ofertas": [
                        {
                            "precio_actual": 12990,
                            "formato_gramos": 250,
                            "precio_por_kilo": 51960.0,
                            "es_estimado": True,
                            "link_detalle": "https://test-pickers.cl/products/qawale",
                            "disponible": True,
                        }
                    ],
                }
            ]

            # Esta llamada antes fallaba con psycopg.errors.StringDataRightTruncation
            db.guardar_cafes_cascada(catalogo, tienda_id=t_id)

            with db.SessionLocal() as session:
                saved_cafe = session.query(Cafe).filter(Cafe.hash_descripcion == "pickers_test_hash_123").first()
                self.assertIsNotNone(saved_cafe)
                self.assertTrue(saved_cafe.lote.startswith("Bourbon, Caturra"))
                self.assertEqual(saved_cafe.lote, long_lote[:255])
        finally:
            with db.SessionLocal() as session:
                t = session.get(Tienda, t_id)
                if t:
                    session.delete(t)
                session.commit()


if __name__ == "__main__":
    unittest.main()

