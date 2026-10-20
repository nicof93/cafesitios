import unittest
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from db.database import Base, Tienda, PedidoWhatsApp
from api.orders import (
    _handle_create_whatsapp_lead,
    WhatsAppLeadCreateRequest,
    WhatsAppOrderItemInput,
)
from api.admin_tienda import (
    update_store_whatsapp_config,
    list_store_whatsapp_orders,
    get_store_whatsapp_metrics,
    StoreWhatsAppConfigRequest,
)
from core.security_store_admin import StoreAdminContext


class DummyRequest:
    def __init__(self, client_host="127.0.0.1"):
        self.client = type("Client", (), {"host": client_host})()
        self.headers = {}


class TestWhatsAppOrdersAndAdmin(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.session = self.Session()

        self.tienda = Tienda(
            nombre="Café El Grano",
            url_base="https://elgrano.cl",
            plataforma="shopify",
            telefono_whatsapp="+56912345678",
            activo=True,
        )
        self.session.add(self.tienda)
        self.session.commit()

        self.context = StoreAdminContext(
            usuario_id="1",
            tienda_id=self.tienda.id,
            rol="propietario",
            tienda=self.tienda,
            ip_origen="10.0.0.1",
        )

    def tearDown(self):
        self.session.close()

    def test_register_whatsapp_lead_success(self):
        req = WhatsAppLeadCreateRequest(
            tienda_id=self.tienda.id,
            dispositivo_uuid="uuid-device-1234",
            monto_total_clp=36500,
            items=[
                WhatsAppOrderItemInput(
                    producto_id="prod-1",
                    nombre="Etiopía Guji",
                    formato="250g",
                    molienda="V60",
                    cantidad=2,
                    precio_unitario_clp=11000,
                ),
                WhatsAppOrderItemInput(
                    producto_id="prod-2",
                    nombre="Colombia Supremo",
                    formato="500g",
                    molienda="Grano entero",
                    cantidad=1,
                    precio_unitario_clp=14500,
                ),
            ],
        )
        dummy_http = DummyRequest(client_host="10.0.0.1")
        resp = _handle_create_whatsapp_lead(req, dummy_http, self.session)
        self.assertTrue(resp.exito)
        self.assertIsNotNone(resp.id)

        # Verificar en base de datos
        saved = self.session.query(PedidoWhatsApp).filter_by(id=resp.id).first()
        self.assertIsNotNone(saved)
        self.assertEqual(saved.tienda_id, self.tienda.id)
        self.assertEqual(saved.monto_total_clp, 36500)
        self.assertEqual(len(saved.items), 2)
        self.assertEqual(saved.estado, "ENVIADO")

    def test_update_whatsapp_config(self):
        body = StoreWhatsAppConfigRequest(telefono_whatsapp="+56987654321")
        dummy_http = DummyRequest(client_host="10.0.0.1")
        res = update_store_whatsapp_config(body, dummy_http, self.context, self.session)
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["telefono_whatsapp"], "+56987654321")

        # Refrescar tienda
        self.session.refresh(self.tienda)
        self.assertEqual(self.tienda.telefono_whatsapp, "+56987654321")

    def test_list_whatsapp_pedidos_and_metrics(self):
        lead1 = PedidoWhatsApp(
            tienda_id=self.tienda.id,
            dispositivo_uuid="uuid-1",
            monto_total_clp=20000,
            items=[{"nombre": "Café A", "cantidad": 1}],
            estado="ENVIADO",
            fecha_creacion=datetime.now(timezone.utc).replace(tzinfo=None),
        )
        lead2 = PedidoWhatsApp(
            tienda_id=self.tienda.id,
            dispositivo_uuid="uuid-2",
            monto_total_clp=15000,
            items=[{"nombre": "Café B", "cantidad": 1}],
            estado="ENVIADO",
            fecha_creacion=datetime.now(timezone.utc).replace(tzinfo=None),
        )
        self.session.add_all([lead1, lead2])
        self.session.commit()

        # Listar pedidos de WhatsApp
        pedidos_resp = list_store_whatsapp_orders(self.context, self.session)
        self.assertEqual(len(pedidos_resp), 2)

        # Métricas
        metrics = get_store_whatsapp_metrics(self.context, self.session)
        self.assertEqual(metrics.ventas_whatsapp_30d, 35000)
        self.assertEqual(metrics.total_pedidos_30d, 2)
        self.assertEqual(metrics.incremento_estimado_clp, 6300)
        self.assertIn("35.000", metrics.texto_proyeccion)
        self.assertIn("18%", metrics.texto_proyeccion)


    def test_whatsapp_orders_disabled_by_feature_flag(self):
        import os
        from fastapi import HTTPException
        from api.dependencies import require_whatsapp_orders_enabled
        os.environ['ENABLE_WHATSAPP_ORDERS'] = 'false'
        try:
            with self.assertRaises(HTTPException) as ctx:
                require_whatsapp_orders_enabled()
            self.assertEqual(ctx.exception.status_code, 404)
        finally:
            os.environ.pop('ENABLE_WHATSAPP_ORDERS', None)

if __name__ == '__main__':
    unittest.main()
