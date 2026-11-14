import unittest
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi import HTTPException

from core.security_store_admin import StoreAdminContext
from db.database import (
    Base,
    Cata,
    CataRespuesta,
    Producto,
    Tienda,
    Variante,
)
from api.admin_tienda import (
    create_store_cata,
    delete_store_cata,
    get_store_cata_detail,
    list_store_catas,
    update_store_cata,
)
from api.catas import (
    get_cata_publica_metadata,
    submit_cata_publica_respuesta,
)
from api.products import get_product_detail
from api.schemas import (
    CataCreateRequest,
    CataRespuestaPublicaRequest,
    CataUpdateRequest,
)


class DummyRequest:
    def __init__(self, headers=None, client_host="192.168.1.50", base_url="https://cafesitios.cl"):
        self.headers = headers or {}
        self.client = type("Client", (), {"host": client_host})()
        self.base_url = base_url


class TestCatasPanelSensorial(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.session = self.Session()

        # Tienda 1
        self.tienda1 = Tienda(
            id=1,
            nombre="Singular Coffee",
            url_base="https://singularcoffee.cl",
            plataforma="shopify",
            activo=True,
            slug="singular-coffee",
        )
        # Tienda 2
        self.tienda2 = Tienda(
            id=2,
            nombre="Triciclo Coffee",
            url_base="https://triciclo.cl",
            plataforma="woocommerce",
            activo=True,
            slug="triciclo",
        )
        self.session.add_all([self.tienda1, self.tienda2])

        # Producto para Tienda 1 (con puntuación SCA oficial para validar dualidad)
        self.prod1 = Producto(
            id=10,
            tienda_id=1,
            nombre="Colombia El Paraíso Diego Bermúdez",
            activo=True,
            oculto_catalogo=False,
            url_detalle="https://singularcoffee.cl/el-paraiso",
            caracteristicas_fuente={"puntuacion_sca": 88.5},
        )
        # Producto para Tienda 2
        self.prod2 = Producto(
            id=20,
            tienda_id=2,
            nombre="Etiopía Guji Natural",
            activo=True,
            oculto_catalogo=False,
            url_detalle="https://triciclo.cl/guji",
        )
        self.session.add_all([self.prod1, self.prod2])
        self.session.flush()

        # Variante mínima para Tienda 1
        self.var1 = Variante(
            id=101,
            producto_id=10,
            id_variante_externo="VAR_101",
            opcion="250g Grano",
            precio_clp=14990,
            precio_original_clp=14990,
            precio_por_kilo=59960.0,
            formato_gramos=250,
            disponible=True,
        )
        self.session.add(self.var1)
        self.session.commit()

        self.ctx1 = StoreAdminContext(
            usuario_id="admin@singularcoffee.cl",
            tienda_id=1,
            tienda=self.tienda1,
            rol="STORE_ADMIN",
            ip_origen="127.0.0.1",
        )
        self.ctx2 = StoreAdminContext(
            usuario_id="admin@triciclo.cl",
            tienda_id=2,
            tienda=self.tienda2,
            rol="STORE_ADMIN",
            ip_origen="127.0.0.1",
        )

        self.dummy_req = DummyRequest()

    def tearDown(self):
        self.session.close()
        self.engine.dispose()

    def test_create_cata_default_name_and_token(self):
        req = CataCreateRequest(
            duracion_horas=24,
            valores_iniciales_75=True,
        )
        cata_dto = create_store_cata(
            payload=req,
            request=self.dummy_req,
            ctx=self.ctx1,
            db_session=self.session,
        )

        today_str = datetime.utcnow().strftime("%Y-%m-%d")
        self.assertEqual(cata_dto.nombre, f"panel-sensorial-{today_str}")
        self.assertTrue(cata_dto.token_publico.startswith("cata_"))
        self.assertTrue(cata_dto.esta_vigente)
        self.assertEqual(cata_dto.estado, "activa")
        self.assertTrue(cata_dto.valores_iniciales_75)
        self.assertEqual(cata_dto.total_respuestas, 0)
        self.assertIsNone(cata_dto.puntaje_promedio)
        self.assertIn(cata_dto.token_publico, cata_dto.url_publica)

    def test_create_cata_with_custom_name_duration_and_product(self):
        req = CataCreateRequest(
            nombre="Calibración Batch Tueste #12",
            descripcion="Evaluación de tueste experimental para espresso",
            duracion_horas=8,
            producto_id=10,
            valores_iniciales_75=False,
        )
        cata_dto = create_store_cata(
            payload=req,
            request=self.dummy_req,
            ctx=self.ctx1,
            db_session=self.session,
        )

        self.assertEqual(cata_dto.nombre, "Calibración Batch Tueste #12")
        self.assertEqual(cata_dto.producto_id, 10)
        self.assertEqual(cata_dto.producto_nombre, "Colombia El Paraíso Diego Bermúdez")
        self.assertFalse(cata_dto.valores_iniciales_75)

    def test_create_cata_rejects_foreign_product(self):
        req = CataCreateRequest(
            nombre="Intento de cata café ajeno",
            producto_id=20,  # Producto de Tienda 2
        )
        with self.assertRaises(HTTPException) as ctx:
            create_store_cata(
                payload=req,
                request=self.dummy_req,
                ctx=self.ctx1,
                db_session=self.session,
            )
        self.assertEqual(ctx.exception.status_code, 400)

    def test_list_store_catas_multi_tenant_isolation(self):
        # Crear cata en Tienda 1
        create_store_cata(
            payload=CataCreateRequest(nombre="Cata T1"),
            request=self.dummy_req,
            ctx=self.ctx1,
            db_session=self.session,
        )
        # Crear cata en Tienda 2
        create_store_cata(
            payload=CataCreateRequest(nombre="Cata T2"),
            request=self.dummy_req,
            ctx=self.ctx2,
            db_session=self.session,
        )

        catas_t1 = list_store_catas(request=self.dummy_req, ctx=self.ctx1, db_session=self.session)
        catas_t2 = list_store_catas(request=self.dummy_req, ctx=self.ctx2, db_session=self.session)

        self.assertEqual(len(catas_t1), 1)
        self.assertEqual(catas_t1[0].nombre, "Cata T1")
        self.assertEqual(len(catas_t2), 1)
        self.assertEqual(catas_t2[0].nombre, "Cata T2")

    def test_public_metadata_endpoint(self):
        cata_dto = create_store_cata(
            payload=CataCreateRequest(
                nombre="Panel Abierto Baristas",
                producto_id=10,
            ),
            request=self.dummy_req,
            ctx=self.ctx1,
            db_session=self.session,
        )

        meta = get_cata_publica_metadata(token=cata_dto.token_publico, db_session=self.session)
        self.assertEqual(meta.nombre, "Panel Abierto Baristas")
        self.assertEqual(meta.tienda_nombre, "Singular Coffee")
        self.assertEqual(meta.producto_nombre, "Colombia El Paraíso Diego Bermúdez")
        self.assertTrue(meta.esta_vigente)

        # Token inexistente -> 404
        with self.assertRaises(HTTPException) as err:
            get_cata_publica_metadata(token="token_invalido_xyz", db_session=self.session)
        self.assertEqual(err.exception.status_code, 404)

    def test_submit_public_cupping_response(self):
        cata_dto = create_store_cata(
            payload=CataCreateRequest(nombre="Panel Sensorial"),
            request=self.dummy_req,
            ctx=self.ctx1,
            db_session=self.session,
        )

        # Catador envía evaluación
        # 10 atributos de 8.5 puntos cada uno = 85.0 - 0 defectos = 85.00
        resp_req = CataRespuestaPublicaRequest(
            nombre_catador="Nicolás Barista",
            fragancia_aroma=8.5,
            sabor=8.5,
            sabor_residual=8.5,
            acidez=8.5,
            cuerpo=8.5,
            uniformidad=8.5,
            balance=8.5,
            taza_limpia=8.5,
            dulzor=8.5,
            puntaje_general=8.5,
            defectos=0.0,
            notas_identificadas=["Jazmín", "Cítricos", "Durazno"],
            observaciones="Acidez brillante muy limpia, final prolongado.",
        )

        res = submit_cata_publica_respuesta(
            token=cata_dto.token_publico,
            payload=resp_req,
            db_session=self.session,
        )
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["nombre_catador"], "Nicolás Barista")
        self.assertEqual(res["puntaje_total"], 85.0)

        # Verificar almacenamiento inmutable
        saved = self.session.query(CataRespuesta).filter(CataRespuesta.cata_id == cata_dto.id).first()
        self.assertIsNotNone(saved)
        self.assertEqual(saved.nombre_catador, "Nicolás Barista")
        self.assertEqual(saved.puntaje_total, 85.0)
        self.assertIn("jazmín", saved.notas_identificadas)
        self.assertIn("cítricos", saved.notas_identificadas)

    def test_submit_public_cupping_rejects_expired_or_closed_cata(self):
        cata_dto = create_store_cata(
            payload=CataCreateRequest(nombre="Panel Sensorial Expirable"),
            request=self.dummy_req,
            ctx=self.ctx1,
            db_session=self.session,
        )

        # Cerrar la cata
        update_store_cata(
            cata_id=cata_dto.id,
            payload=CataUpdateRequest(estado="cerrada"),
            request=self.dummy_req,
            ctx=self.ctx1,
            db_session=self.session,
        )

        resp_req = CataRespuestaPublicaRequest(
            nombre_catador="Catador Tardío",
            fragancia_aroma=7.5,
            sabor=7.5,
            sabor_residual=7.5,
            acidez=7.5,
            cuerpo=7.5,
            uniformidad=10.0,
            balance=7.5,
            taza_limpia=10.0,
            dulzor=10.0,
            puntaje_general=7.5,
        )
        with self.assertRaises(HTTPException) as ctx:
            submit_cata_publica_respuesta(
                token=cata_dto.token_publico,
                payload=resp_req,
                db_session=self.session,
            )
        self.assertEqual(ctx.exception.status_code, 400)

    def test_get_store_cata_detail_aggregations_and_immutability(self):
        cata_dto = create_store_cata(
            payload=CataCreateRequest(nombre="Cata Resumen"),
            request=self.dummy_req,
            ctx=self.ctx1,
            db_session=self.session,
        )

        # Respuesta 1: Catador A (82.5 pts)
        submit_cata_publica_respuesta(
            token=cata_dto.token_publico,
            payload=CataRespuestaPublicaRequest(
                nombre_catador="Catador A",
                fragancia_aroma=8.0,
                sabor=8.0,
                sabor_residual=8.0,
                acidez=8.0,
                cuerpo=8.0,
                uniformidad=10.0,
                balance=8.0,
                taza_limpia=10.0,
                dulzor=10.0,
                puntaje_general=8.0,
                defectos=0.0,  # 86.0
                notas_identificadas=["chocolate", "cítricos"],
            ),
            db_session=self.session,
        )

        # Respuesta 2: Catador B (84.0 pts)
        submit_cata_publica_respuesta(
            token=cata_dto.token_publico,
            payload=CataRespuestaPublicaRequest(
                nombre_catador="Catador B",
                fragancia_aroma=8.0,
                sabor=8.0,
                sabor_residual=7.5,
                acidez=8.0,
                cuerpo=7.5,
                uniformidad=10.0,
                balance=8.0,
                taza_limpia=10.0,
                dulzor=10.0,
                puntaje_general=7.5,
                defectos=0.0,  # 84.5
                notas_identificadas=["cítricos", "jazmín"],
            ),
            db_session=self.session,
        )

        detail = get_store_cata_detail(
            cata_id=cata_dto.id,
            request=self.dummy_req,
            ctx=self.ctx1,
            db_session=self.session,
        )

        self.assertEqual(detail.total_respuestas, 2)
        # (86.0 + 84.5) / 2 = 85.25
        self.assertEqual(detail.puntaje_promedio, 85.25)
        self.assertEqual(detail.promedio_atributos["acidez"], 8.0)
        self.assertEqual(len(detail.respuestas), 2)

        # "cítricos" apareció en ambas respuestas, debe ser la nota #1
        self.assertEqual(detail.frecuencia_notas[0]["nota"], "cítricos")
        self.assertEqual(detail.frecuencia_notas[0]["conteo"], 2)

    def test_update_cata_and_publish_on_product(self):
        cata_dto = create_store_cata(
            payload=CataCreateRequest(nombre="Cata para Ficha"),
            request=self.dummy_req,
            ctx=self.ctx1,
            db_session=self.session,
        )

        # Agregar respuesta con 86.5 pts
        submit_cata_publica_respuesta(
            token=cata_dto.token_publico,
            payload=CataRespuestaPublicaRequest(
                nombre_catador="Catador Principal",
                fragancia_aroma=8.5,
                sabor=8.5,
                sabor_residual=8.0,
                acidez=8.5,
                cuerpo=8.5,
                uniformidad=10.0,
                balance=8.5,
                taza_limpia=10.0,
                dulzor=10.0,
                puntaje_general=8.5,
                defectos=0.0,
                notas_identificadas=["frambuesa", "jazmín"],
            ),
            db_session=self.session,
        )

        # Antes de asociar y publicar: el detalle del café NO tiene panel_cata
        prod_detail_antes = get_product_detail(product_id=10, db_session=self.session)
        self.assertIsNone(prod_detail_antes.get("panel_cata"))
        # Pero sí tiene su puntuación SCA oficial
        self.assertEqual(prod_detail_antes.get("puntuacion_sca"), 88.5)

        # Asociar la cata al producto 10 y activar publicar_en_producto
        update_store_cata(
            cata_id=cata_dto.id,
            payload=CataUpdateRequest(
                producto_id=10,
                publicar_en_producto=True,
            ),
            request=self.dummy_req,
            ctx=self.ctx1,
            db_session=self.session,
        )

        # Ahora el detalle del café DEBE incluir panel_cata complementario y diferenciado
        prod_detail_despues = get_product_detail(product_id=10, db_session=self.session)
        panel_info = prod_detail_despues.get("panel_cata")
        self.assertIsNotNone(panel_info)
        self.assertEqual(panel_info["nombre_cata"], "Cata para Ficha")
        self.assertEqual(panel_info["puntaje_promedio"], 89.0)
        self.assertEqual(panel_info["total_evaluadores"], 1)
        self.assertIn("frambuesa", panel_info["notas_destacadas"])
        # Y la puntuación SCA oficial sigue existiendo intacta
        self.assertEqual(prod_detail_despues.get("puntuacion_sca"), 88.5)

    def test_delete_cata_cascades(self):
        cata_dto = create_store_cata(
            payload=CataCreateRequest(nombre="Cata a Borrar"),
            request=self.dummy_req,
            ctx=self.ctx1,
            db_session=self.session,
        )
        submit_cata_publica_respuesta(
            token=cata_dto.token_publico,
            payload=CataRespuestaPublicaRequest(
                nombre_catador="Catador Temporal",
                fragancia_aroma=7.5,
                sabor=7.5,
                sabor_residual=7.5,
                acidez=7.5,
                cuerpo=7.5,
                uniformidad=10.0,
                balance=7.5,
                taza_limpia=10.0,
                dulzor=10.0,
                puntaje_general=7.5,
            ),
            db_session=self.session,
        )

        # Borrar cata
        res = delete_store_cata(
            cata_id=cata_dto.id,
            request=self.dummy_req,
            ctx=self.ctx1,
            db_session=self.session,
        )
        self.assertTrue(res["ok"])

        # Verificar que la cata y sus respuestas se eliminaron
        cata_in_db = self.session.query(Cata).filter(Cata.id == cata_dto.id).first()
        self.assertIsNone(cata_in_db)
        resp_in_db = self.session.query(CataRespuesta).filter(CataRespuesta.cata_id == cata_dto.id).all()
        self.assertEqual(len(resp_in_db), 0)


if __name__ == "__main__":
    unittest.main()
