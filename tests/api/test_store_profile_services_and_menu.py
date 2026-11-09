import base64
import io
import unittest
from datetime import datetime, timezone
from fastapi import HTTPException, Response
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.admin import (
    admin_delete_store_menu_pdf,
    admin_upload_store_menu_pdf,
)
from api.admin_tienda import (
    delete_store_menu_pdf,
    get_store_profile,
    update_store_profile,
    upload_store_menu_pdf,
    StoreMenuPdfUploadRequest,
    StoreProfileUpdateRequest,
)
from api.stores import get_store_public_detail
from core.security_store_admin import StoreAdminContext
from db.database import Base, NovedadTienda, Producto, SucursalTienda, Tienda, Variante


class TestStoreProfileServicesAndMenu(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.session = self.Session()

        # Tienda 1
        self.tienda1 = Tienda(
            id=1,
            nombre="Café Sol",
            url_base="https://cafesol.cl",
            plataforma="woocommerce",
            activo=True,
            slug="cafe-sol",
            descripcion="Tostaduría artesanal en Santiago Centro",
            servicios=["cafeteria_especialidad", "filtrados", "wifi"],
            limite_almacenamiento_mb=250,
        )
        # Tienda 2
        self.tienda2 = Tienda(
            id=2,
            nombre="Café Luna",
            url_base="https://cafeluna.cl",
            plataforma="shopify",
            activo=True,
            slug="cafe-luna",
            limite_almacenamiento_mb=250,
        )
        self.session.add_all([self.tienda1, self.tienda2])

        # Sucursal para Tienda 1
        self.sucursal = SucursalTienda(
            id=1,
            tienda_id=1,
            nombre="Casa Matriz",
            direccion="Moneda 1234",
            comuna="Santiago",
            activo=True,
        )
        self.session.add(self.sucursal)

        # Novedad para Tienda 1
        self.novedad = NovedadTienda(
            id=1,
            tienda_id=1,
            titulo="Nueva carta de invierno",
            descripcion="Prueba nuestros cafés de origen Etiopía",
            activo=True,
        )
        self.session.add(self.novedad)

        # Producto para Tienda 1
        self.prod = Producto(
            id=10,
            tienda_id=1,
            nombre="Etiopía Yirgacheffe",
            activo=True,
            oculto_catalogo=False,
            url_detalle="https://cafesol.cl/etiopia",
        )
        self.session.add(self.prod)
        self.session.flush()

        self.var = Variante(
            id=101,
            producto_id=10,
            id_variante_externo="VAR_101",
            opcion="250g Grano",
            precio_clp=12990,
            precio_original_clp=12990,
            precio_por_kilo=51960.0,
            formato_gramos=250,
            disponible=True,
        )
        self.session.add(self.var)
        self.session.commit()

        self.ctx1 = StoreAdminContext(
            usuario_id="admin@cafesol.cl",
            tienda_id=1,
            tienda=self.tienda1,
            rol="STORE_ADMIN",
            ip_origen="127.0.0.1",
        )

        self.ctx2 = StoreAdminContext(
            usuario_id="admin@cafeluna.cl",
            tienda_id=2,
            tienda=self.tienda2,
            rol="STORE_ADMIN",
            ip_origen="127.0.0.1",
        )

    async def asyncTearDown(self):
        self.session.close()

    def test_get_store_profile_returns_new_fields(self):
        profile = get_store_profile(ctx=self.ctx1, db_session=self.session)
        self.assertEqual(profile.slug, "cafe-sol")
        self.assertEqual(profile.descripcion, "Tostaduría artesanal en Santiago Centro")
        self.assertIn("cafeteria_especialidad", profile.servicios)
        self.assertIn("filtrados", profile.servicios)
        self.assertIn("wifi", profile.servicios)

    def test_update_store_profile_valid(self):
        req = StoreProfileUpdateRequest(
            slug="cafe-sol-chile",
            descripcion="El mejor café de Santiago",
            servicios=["cafeteria_especialidad", "pet_friendly", "terraza"],
            instagram_url="https://instagram.com/cafesol",
        )
        updated = update_store_profile(payload=req, ctx=self.ctx1, db_session=self.session)
        self.assertEqual(updated.slug, "cafe-sol-chile")
        self.assertEqual(updated.descripcion, "El mejor café de Santiago")
        self.assertEqual(set(updated.servicios), {"cafeteria_especialidad", "pet_friendly", "terraza"})
        self.assertEqual(updated.instagram_url, "https://instagram.com/cafesol")

    def test_update_store_profile_invalid_slug_format(self):
        req = StoreProfileUpdateRequest(slug="slug invalido con espacios!!")
        # El slugify lo limpia o si no cumple is_valid_slug se rechaza
        with self.assertRaises(HTTPException) as cm:
            update_store_profile(payload=req, ctx=self.ctx1, db_session=self.session)
        # Note: slugify("slug invalido con espacios!!") produces "slug-invalido-con-espacios"
        # Let's test a slug that results in empty or invalid
        req2 = StoreProfileUpdateRequest(slug="---")
        with self.assertRaises(HTTPException) as cm2:
            update_store_profile(payload=req2, ctx=self.ctx1, db_session=self.session)
        self.assertEqual(cm2.exception.status_code, 400)

    def test_update_store_profile_slug_collision(self):
        # Tienda 2 intenta usar el slug de Tienda 1
        req = StoreProfileUpdateRequest(slug="cafe-sol")
        with self.assertRaises(HTTPException) as cm:
            update_store_profile(payload=req, ctx=self.ctx2, db_session=self.session)
        self.assertEqual(cm.exception.status_code, 400)
        self.assertIn("ya está en uso", cm.exception.detail)

    def test_upload_menu_pdf_rejects_non_pdf(self):
        fake_b64 = "data:text/plain;base64," + base64.b64encode(b"Hello text not pdf").decode("ascii")
        req = StoreMenuPdfUploadRequest(pdf_base64=fake_b64, nombre_archivo="menu.txt")
        with self.assertRaises(HTTPException) as cm:
            upload_store_menu_pdf(payload=req, ctx=self.ctx1, db_session=self.session)
        self.assertEqual(cm.exception.status_code, 400)

    def test_upload_and_delete_menu_pdf(self):
        fake_pdf_content = b"%PDF-1.4 dummy pdf content for menu"
        fake_b64 = "data:application/pdf;base64," + base64.b64encode(fake_pdf_content).decode("ascii")
        req = StoreMenuPdfUploadRequest(pdf_base64=fake_b64, nombre_archivo="carta.pdf")

        res = upload_store_menu_pdf(payload=req, ctx=self.ctx1, db_session=self.session)
        self.assertTrue(res["ok"])
        self.assertIn(".pdf", res["carta_comida_url"])

        # Check DB updated
        t = self.session.get(Tienda, 1)
        self.assertEqual(t.carta_comida_url, f"/static/uploads/tiendas/1/carta_comida.pdf")
        self.assertEqual(t.carta_comida_tamano_bytes, len(fake_pdf_content))

        # Now delete
        del_res = delete_store_menu_pdf(ctx=self.ctx1, db_session=self.session)
        self.assertTrue(del_res["ok"])
        self.assertIsNone(t.carta_comida_url)
        self.assertEqual(t.carta_comida_tamano_bytes, 0)

    def test_get_store_public_detail_by_slug_and_id(self):
        resp = Response()
        # Consulta por slug
        detail = get_store_public_detail(slug_o_id="cafe-sol", response=resp, db_session=self.session)
        self.assertEqual(detail.id, 1)
        self.assertEqual(detail.nombre, "Café Sol")
        self.assertEqual(detail.slug, "cafe-sol")
        self.assertEqual(detail.cantidad_productos, 1)
        self.assertEqual(len(detail.sucursales), 1)
        self.assertEqual(detail.sucursales[0].nombre, "Casa Matriz")
        self.assertEqual(len(detail.novedades), 1)
        self.assertEqual(detail.novedades[0].titulo, "Nueva carta de invierno")
        self.assertEqual(len(detail.cafes_populares), 1)
        self.assertEqual(detail.cafes_populares[0].nombre, "Etiopía Yirgacheffe")
        self.assertIn("cafeteria_especialidad", detail.servicios)

        # Consulta por ID
        detail_by_id = get_store_public_detail(slug_o_id="1", response=resp, db_session=self.session)
        self.assertEqual(detail_by_id.id, 1)
        self.assertEqual(detail_by_id.slug, "cafe-sol")

    def test_get_store_public_detail_not_found(self):
        resp = Response()
        with self.assertRaises(HTTPException) as cm:
            get_store_public_detail(slug_o_id="tienda-inexistente", response=resp, db_session=self.session)
        self.assertEqual(cm.exception.status_code, 404)

    def test_superadmin_upload_and_delete_menu_pdf(self):
        fake_pdf_content = b"%PDF-1.4 dummy superadmin pdf"
        fake_b64 = "data:application/pdf;base64," + base64.b64encode(fake_pdf_content).decode("ascii")
        req = StoreMenuPdfUploadRequest(pdf_base64=fake_b64, nombre_archivo="menu_superadmin.pdf")

        res = admin_upload_store_menu_pdf(store_id=2, payload=req, db_session=self.session)
        self.assertTrue(res["ok"])
        self.assertEqual(res["carta_comida_url"], "/static/uploads/tiendas/2/carta_comida.pdf")

        t2 = self.session.get(Tienda, 2)
        self.assertEqual(t2.carta_comida_url, "/static/uploads/tiendas/2/carta_comida.pdf")

        del_res = admin_delete_store_menu_pdf(store_id=2, db_session=self.session)
        self.assertTrue(del_res["ok"])
        self.assertIsNone(t2.carta_comida_url)


if __name__ == "__main__":
    unittest.main()
