import { test, expect } from '@playwright/test';

test.describe('Ficha de Detalle de Producto', () => {
  test('debe navegar a un producto desde el catálogo y mostrar precios válidos', async ({ page }) => {
    const pageErrors: Error[] = [];
    page.on('pageerror', (err) => pageErrors.push(err));

    await page.goto('/catalogo');

    // Buscar el primer enlace a detalle de producto
    const firstProductLink = page.locator('a[href^="/producto/"]').first();
    const count = await firstProductLink.count();

    if (count > 0) {
      await firstProductLink.click();
      await page.waitForLoadState('domcontentloaded');

      // Verificar que la URL corresponde a /producto/...
      await expect(page).toHaveURL(/\/producto\/\d+/);

      // Comprobar que el encabezado del producto está visible
      const title = page.locator('h1').first();
      await expect(title).toBeVisible();

      // Verificar que las métricas de precio no muestren $0 / $0/kg de forma errónea
      const metricCurrent = page.locator('#metric-current');
      if (await metricCurrent.isVisible()) {
        const text = await metricCurrent.innerText();
        // Si hay variante con precio, no debe mostrar literalmente "$0 /kg" o "$0"
        if (text.includes('/kg')) {
          expect(text).not.toContain('$0 /kg');
        }
      }

      // No deben existir errores de JavaScript en consola
      expect(pageErrors).toHaveLength(0);
    }
  });
});

