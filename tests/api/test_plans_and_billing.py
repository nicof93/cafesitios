import unittest
from datetime import datetime, date, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from api.app_plataforma import create_plataforma_app
from api.app_public import create_public_app
from api.dependencies import get_db_session, require_local_admin
from core.billing_utils import (
    calcular_balance_roi,
    calcular_funcionalidades_efectivas,
    calcular_proxima_fecha_pago,
)
from core.security_store_admin import create_store_admin_token, get_current_store_admin, StoreAdminContext
from db.database import (
    Base,
    InteraccionClic,
    PagoTienda,
    PedidoWhatsApp,
    PlanTienda,
    Producto,
    Tienda,
    UsuarioTienda,
)


class TestBillingUtils(unittest.TestCase):
    def test_calcular_proxima_fecha_pago(self):
        # Si hoy es 4 de noviembre y el día de pago es el 5, próximo pago es 5 de noviembre
        hoy = datetime(2026, 11, 4, 10, 0, 0)
        prox = calcular_proxima_fecha_pago(5, hoy)
        self.assertEqual(prox.date(), date(2026, 11, 5))

        # Si hoy es 6 de noviembre y el día de pago es el 5, próximo pago es 5 de diciembre
        hoy2 = datetime(2026, 11, 6, 10, 0, 0)
        prox2 = calcular_proxima_fecha_pago(5, hoy2)
        self.assertEqual(prox2.date(), date(2026, 12, 5))

        # Fin de año: si hoy es 20 de diciembre y el día de pago es el 10, próximo pago es 10 de enero del año siguiente
        hoy3 = datetime(2026, 12, 20, 10, 0, 0)
        prox3 = calcular_proxima_fecha_pago(10, hoy3)
        self.assertEqual(prox3.date(), date(2027, 1, 10))

        # Clamp de fin de mes: día 31 en febrero no bisiesto se ajusta al día 28
        hoy4 = datetime(2027, 2, 1, 10, 0, 0)
        prox4 = calcular_proxima_fecha_pago(31, hoy4)
        self.assertEqual(prox4.date(), date(2027, 2, 28))

    def test_calcular_funcionalidades_efectivas(self):
        plan_func = {
            "whatsapp_orders": True,
            "recetas_oficiales": True,
            "radar_demanda": False,
        }
        override = {
            "radar_demanda": True,
            "whatsapp_orders": False,
        }
        res = calcular_funcionalidades_efectivas(plan_func, override)
        self.assertFalse(res["whatsapp_orders"])
        self.assertTrue(res["recetas_oficiales"])
        self.assertTrue(res["radar_demanda"])
        self.assertFalse(res["benchmark_precios"])

    def test_calcular_balance_roi(self):
        # 10 pedidos con total $120.000, 100 clics salientes ($35.000 valor), plan de $19.990
        # Total valor: $155.000 -> ratio: round((155000 / 19990)*100, 1) = 775.4%
        res = calcular_balance_roi(
            ventas_whatsapp_clp=120000,
            total_pedidos_whatsapp=10,
            clics_salientes=100,
            costo_mensual_clp=19990,
        )
        self.assertEqual(res["total_pedidos_whatsapp"], 10)
        self.assertEqual(res["monto_ventas_whatsapp_clp"], 120000)
        self.assertEqual(res["total_clics_salientes"], 100)
        self.assertEqual(res["valor_estimado_clics_clp"], 35000)
        self.assertEqual(res["valor_total_generado_clp"], 155000)
        self.assertEqual(res["balance_neto_clp"], 135010)
        self.assertGreaterEqual(res["ratio_cobertura_porcentaje"], 200.0)
        self.assertIn("Retorno excepcional", res["mensaje_retorno"])


class TestPlansAndBillingApi(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(cls.engine)
        cls.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=cls.engine)

        # Aplicación Superadmin (puerto 8001 / plataforma)
        cls.admin_app = create_plataforma_app()
        cls.admin_app.dependency_overrides[get_db_session] = cls._get_db_override
        cls.admin_app.dependency_overrides[require_local_admin] = lambda: True
        cls.admin_client = TestClient(cls.admin_app)

        # Aplicación Pública y Admin Tienda (puerto 8000 / main)
        cls.public_app = create_public_app()
        cls.public_app.dependency_overrides[get_db_session] = cls._get_db_override
        cls.public_client = TestClient(cls.public_app)

    @classmethod
    def tearDownClass(cls):
        Base.metadata.drop_all(cls.engine)
        cls.engine.dispose()

    @classmethod
    def _get_db_override(cls):
        db = cls.SessionLocal()
        try:
            yield db
        finally:
            db.close()

    def setUp(self):
        self.session = self.SessionLocal()

        # Seed plan
        self.plan_pro = PlanTienda(
            nombre="Plan Pro Test",
            codigo="pro_test",
            precio_mensual_clp=19990,
            descripcion="Plan para pruebas",
            limite_almacenamiento_mb=500,
            funcionalidades={"whatsapp_orders": True, "recetas_oficiales": True},
            activo=True,
            fecha_creacion=datetime.utcnow(),
            fecha_actualizacion=datetime.utcnow(),
        )
        self.session.add(self.plan_pro)
        self.session.commit()
        self.session.refresh(self.plan_pro)

        # Seed tienda
        self.tienda = Tienda(
            nombre="Tostaduría Valparaíso",
            url_base="https://valparaisocoffee.cl",
            plataforma="shopify",
            activo=True,
            plan_id=self.plan_pro.id,
            dia_pago_mensual=15,
            precio_acordado_clp=17990,  # Descuento acordado
            estado_pago="AL_DIA",
        )
        self.session.add(self.tienda)
        self.session.commit()
        self.session.refresh(self.tienda)

        # Contexto de autenticación para Store Admin
        self.store_ctx = StoreAdminContext(
            tienda_id=self.tienda.id,
            usuario_id="1",
            rol="propietario",
            tienda=self.tienda,
            ip_origen="127.0.0.1",
        )

    def tearDown(self):
        self.session.query(PagoTienda).delete()
        self.session.query(PedidoWhatsApp).delete()
        self.session.query(InteraccionClic).delete()
        self.session.query(Producto).delete()
        self.session.query(Tienda).delete()
        self.session.query(PlanTienda).delete()
        self.session.commit()
        self.session.close()

    def test_admin_crud_planes(self):
        # Listar planes
        resp = self.admin_client.get("/api/v1/administracion/planes")
        self.assertEqual(resp.status_code, 200)
        planes = resp.json()
        self.assertGreaterEqual(len(planes), 1)
        self.assertEqual(planes[0]["codigo"], "pro_test")
        self.assertEqual(planes[0]["total_tiendas"], 1)

        # Crear nuevo plan
        payload = {
            "nombre": "Plan Enterprise",
            "codigo": "enterprise",
            "precio_mensual_clp": 59990,
            "descripcion": "Plan corporativo",
            "limite_almacenamiento_mb": 5000,
            "funcionalidades": {
                "whatsapp_orders": True,
                "recetas_oficiales": True,
                "radar_demanda": True,
                "benchmark_precios": True,
            },
            "activo": True,
        }
        resp_post = self.admin_client.post("/api/v1/administracion/planes", json=payload)
        self.assertEqual(resp_post.status_code, 201)
        created = resp_post.json()
        self.assertEqual(created["codigo"], "enterprise")
        self.assertEqual(created["precio_mensual_clp"], 59990)

        # Modificar plan
        plan_id = created["id"]
        update_payload = dict(payload)
        update_payload["precio_mensual_clp"] = 64990
        resp_put = self.admin_client.put(f"/api/v1/administracion/planes/{plan_id}", json=update_payload)
        self.assertEqual(resp_put.status_code, 200)
        self.assertEqual(resp_put.json()["precio_mensual_clp"], 64990)

    def test_admin_tiendas_suscripciones_y_cobranzas(self):
        # Listar suscripciones de tiendas
        resp = self.admin_client.get("/api/v1/administracion/tiendas-suscripciones")
        self.assertEqual(resp.status_code, 200)
        items = resp.json()
        self.assertEqual(len(items), 1)
        item = items[0]
        self.assertEqual(item["nombre"], "Tostaduría Valparaíso")
        self.assertEqual(item["dia_pago_mensual"], 15)
        self.assertEqual(item["precio_acordado_clp"], 17990)
        self.assertEqual(item["precio_efectivo_clp"], 17990)
        self.assertEqual(item["plan_nombre"], "Plan Pro Test")

        # Actualizar día de pago y overrides de funcionalidades
        upd = {
            "dia_pago_mensual": 28,
            "precio_acordado_clp": 15000,
            "funcionalidades_override": {"radar_demanda": True},
        }
        resp_upd = self.admin_client.put(f"/api/v1/administracion/tiendas/{self.tienda.id}/suscripcion", json=upd)
        self.assertEqual(resp_upd.status_code, 200)
        data_upd = resp_upd.json()
        self.assertEqual(data_upd["dia_pago_mensual"], 28)
        self.assertEqual(data_upd["precio_efectivo_clp"], 15000)
        self.assertTrue(data_upd["funcionalidades_efectivas"]["radar_demanda"])

        # Registrar un pago
        pago_payload = {
            "monto_clp": 15000,
            "periodo_mes": 11,
            "periodo_anio": 2026,
            "metodo_pago": "TRANSFERENCIA",
            "referencia_comprobante": "TRF-987654",
            "notas": "Mensualidad Noviembre 2026",
        }
        resp_pago = self.admin_client.post(f"/api/v1/administracion/tiendas/{self.tienda.id}/pagos", json=pago_payload)
        self.assertEqual(resp_pago.status_code, 201)
        pago_data = resp_pago.json()
        self.assertEqual(pago_data["monto_clp"], 15000)
        self.assertEqual(pago_data["referencia_comprobante"], "TRF-987654")

        # Listar pagos de la tienda
        resp_lista_pagos = self.admin_client.get(f"/api/v1/administracion/tiendas/{self.tienda.id}/pagos")
        self.assertEqual(resp_lista_pagos.status_code, 200)
        self.assertEqual(len(resp_lista_pagos.json()), 1)

    def test_store_admin_portal_suscripcion_y_roi(self):
        # Override de autenticación de tienda
        self.public_app.dependency_overrides[get_current_store_admin] = lambda: self.store_ctx

        # Producto de la tienda
        prod = Producto(
            tienda_id=self.tienda.id,
            nombre="Café Geisha",
            url_detalle="https://valparaisocoffee.cl/products/geisha",
            activo=True,
        )
        self.session.add(prod)
        self.session.commit()
        self.session.refresh(prod)

        # Generar interacciones de tracción para el ROI
        # 1 pedido por WhatsApp de $25.000
        pedido = PedidoWhatsApp(
            tienda_id=self.tienda.id,
            dispositivo_uuid="test-device-123",
            monto_total_clp=25000,
            items=[{"nombre": "Café Bourbon", "cantidad": 1, "precio": 25000}],
            fecha_creacion=datetime.utcnow() - timedelta(days=2),
            estado="ENVIADO",
        )
        # 20 clics salientes
        for _ in range(20):
            clic = InteraccionClic(
                producto_id=prod.id,
                tipo_evento="outbound_store_click",
                ip_hash="hash-123",
                fecha_creacion=datetime.utcnow() - timedelta(days=1),
            )
            self.session.add(clic)
        self.session.add(pedido)
        self.session.commit()

        # Consultar portal de suscripción desde la tienda
        resp = self.public_client.get("/api/v1/admin/tienda/suscripcion")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()

        # Validar plan y próximo cobro
        self.assertEqual(data["precio_mensual_clp"], 17990)
        self.assertEqual(data["dia_pago_mensual"], 15)
        self.assertTrue(len(data["fecha_proximo_pago"]) > 0)
        self.assertEqual(data["estado_pago"], "AL_DIA")

        # Validar ROI
        roi = data["balance_roi"]
        self.assertEqual(roi["total_pedidos_whatsapp"], 1)
        self.assertEqual(roi["monto_ventas_whatsapp_clp"], 25000)
        self.assertEqual(roi["total_clics_salientes"], 20)
        # 20 * 350 = 7.000 + 25.000 = 32.000 generado
        self.assertEqual(roi["valor_total_generado_clp"], 32000)
        self.assertEqual(roi["costo_mensual_suscripcion_clp"], 17990)
        self.assertEqual(roi["balance_neto_clp"], 32000 - 17990)
        self.assertGreater(roi["ratio_cobertura_porcentaje"], 100.0)


if __name__ == "__main__":
    unittest.main()
