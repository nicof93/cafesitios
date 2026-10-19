import { test, expect } from '@playwright/test';

test.describe('Catálogo y Exploración Pública', () => {
  test('debe cargar la página del catálogo sin errores no controlados', async ({ page }) => {
    const pageErrors: Error[] = [];
    page.on('pageerror', (err) => pageErrors.push(err));

    await page.goto('/catalogo');

    // Comprobar título o encabezado principal
    await expect(page).toHaveTitle(/Café|Cafesitios|Catálogo/i);
    const heading = page.locator('main h1').first();
    await expect(heading).toBeVisible();

    // Comprobar que no hay errores de ejecución de scripts en cliente
    expect(pageErrors).toHaveLength(0);
  });

  test('el buscador del catálogo debe ser interactivo', async ({ page }) => {
    await page.goto('/catalogo');

    const searchInput = page.locator('input[type="search"], input[placeholder*="Buscar"]').first();
    if (await searchInput.isVisible()) {
      await searchInput.fill('Geisha');
      await expect(searchInput).toHaveValue('Geisha');
    }
  });
});

