import { test, expect } from '@playwright/test';

test.describe('Preparador de Pedidos por WhatsApp y Leads', () => {
  test('debe mostrar el banner informativo de transparencia en el header', async ({ page }) => {
    await page.goto('/catalogo');

    const banner = page.locator('text=Los pedidos se envían directamente por WhatsApp a la tostaduría');
    await expect(banner).toBeVisible();
    await expect(page.locator('text=Cafesitios no cobra comisiones ni procesa pagos en línea')).toBeVisible();
  });

  test('el drawer del carrito debe abrirse y cerrarse correctamente', async ({ page }) => {
    await page.goto('/catalogo');

    const btnOpenCart = page.locator('#btn-open-cart');
    await expect(btnOpenCart).toBeVisible();

    // Abrir drawer
    await btnOpenCart.click();
    const drawer = page.locator('#cart-drawer');
    await expect(drawer).toBeVisible();
    await expect(page.locator('#cart-empty-state')).toBeVisible();

    // Cerrar drawer
    const btnCloseCart = page.locator('#btn-close-cart');
    await btnCloseCart.click();
    await expect(drawer).not.toHaveClass(/translate-x-0/);
  });

  test('debe poder agregar un ítem al carrito y calcular subtotales', async ({ page }) => {
    await page.goto('/catalogo');

    // Inyectar un ítem directamente en localStorage simulando la acción de compra
    await page.evaluate(() => {
      localStorage.setItem('cafesitios_cart_v1', JSON.stringify([
        {
          id: 'prod-1_250_Grano',
          productId: 1,
          nombre: 'Etiopía Yirgacheffe Test',
          formatoGramos: 250,
          molienda: 'V60',
          cantidad: 2,
          precioUnitarioClp: 12000,
          tiendaId: 10,
          tiendaNombre: 'Tostaduría Muestra',
          tiendaWhatsapp: '+56912345678',
        }
      ]));
      window.dispatchEvent(new CustomEvent('cafesitios:cart-updated'));
    });

    // Abrir carrito y verificar el renderizado agrupado
    const btnOpenCart = page.locator('#btn-open-cart');
    await btnOpenCart.click();

    await expect(page.locator('text=Tostaduría Muestra')).toBeVisible();
    await expect(page.locator('text=Etiopía Yirgacheffe Test')).toBeVisible();
    await expect(page.locator('text=$24.000 CLP').first()).toBeVisible();
    await expect(page.locator('text=Encargar por WhatsApp ($24.000 CLP)')).toBeVisible();
  });

  test('en el panel de administración debe existir la configuración de WhatsApp y las métricas', async ({ page }) => {
    // Interceptar llamadas API de admin-tienda
    await page.route('**/api/v1/admin/tienda/perfil', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          tienda_id: 1,
          tienda_nombre: 'Café Singular Test',
          tienda_url: 'https://singularcoffee.cl',
          total_productos: 12,
          plataforma: 'Shopify',
          rol: 'STORE_ADMIN',
          telefono_whatsapp: '+56912345678',
        }),
      });
    });

    await page.route('**/api/v1/admin/tienda/whatsapp/metricas', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          ventas_whatsapp_30d: 36500,
          total_pedidos_30d: 3,
          incremento_estimado_clp: 6570,
          texto_proyeccion: 'Tus clientes han solicitado $36.500 CLP en pedidos por WhatsApp este mes.',
        }),
      });
    });

    await page.route('**/api/v1/admin/tienda/whatsapp/pedidos', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([
          {
            id: 101,
            tienda_id: 1,
            dispositivo_uuid: 'uuid-test-1234',
            monto_total_clp: 36500,
            items: [
              { nombre: 'Etiopía Guji', cantidad: 2, formato: '250g' }
            ],
            estado: 'ENVIADO',
            fecha_creacion: new Date().toISOString(),
          }
        ]),
      });
    });

    // Simular sesión autenticada
    await page.addInitScript(() => {
      localStorage.setItem('store_admin_token', 'fake-jwt-token-testing');
    });

    await page.goto('/admin-tienda/dashboard');

    // Verificar sección WhatsApp comercial
    await expect(page.locator('text=WhatsApp Comercial de Ventas')).toBeVisible();
    await expect(page.locator('#input-whatsapp-phone')).toHaveValue('912345678');

    // Verificar KPIs y Proyección financiera
    await expect(page.locator('#kpi-whatsapp-sales')).toHaveText('$36.500 CLP');
    await expect(page.locator('#kpi-whatsapp-orders-count')).toHaveText('3 pedidos recibidos');
    await expect(page.locator('#kpi-whatsapp-boost')).toHaveText('+$6.570 CLP');
    await expect(page.locator('#kpi-whatsapp-projection-text')).toContainText('$36.500 CLP');

    // Verificar tabla de pedidos
    await expect(page.locator('text=Etiopía Guji (250g)')).toBeVisible();
  });
});
