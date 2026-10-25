import { test, expect } from '@playwright/test';

test.describe('Glosario de Café de Especialidad (/glosario)', () => {
  test('debe cargar la enciclopedia de términos y renderizar los conceptos sin errores', async ({ page }) => {
    const pageErrors: Error[] = [];
    page.on('pageerror', (err) => pageErrors.push(err));

    await page.goto('/glosario');

    // 1. Título principal semántico h1
    const h1 = page.getByRole('heading', { level: 1, name: /Glosario de Café de Especialidad/i });
    await expect(h1).toBeVisible();

    // 2. Buscador reactivo presente
    const searchInput = page.locator('#glossary-search-input');
    await expect(searchInput).toBeVisible();

    // 3. Infografía 3D de anatomía del grano presente e interactiva
    const infografia = page.locator('#anatomia-grano');
    await expect(infografia).toBeVisible();

    const headingAnatomia = page.getByRole('heading', { name: /Anatomía 3D de la Cereza/i });
    await expect(headingAnatomia).toBeVisible();

    // Cambiar a vista explotada
    const btnExplotada = page.getByRole('button', { name: /Explotada/i });
    await btnExplotada.click();

    // 4. Tarjetas de términos renderizadas
    const cards = page.locator('.glossary-card');
    const count = await cards.count();
    expect(count).toBeGreaterThanOrEqual(28);

    // 4. Filtrar por término 'honey'
    await searchInput.fill('honey');
    const cardHoney = page.locator('#proceso-honey');
    await expect(cardHoney).toBeVisible();

    // 5. Verificar que términos no relacionados queden ocultos
    const cardGeisha = page.locator('#variedad-geisha');
    await expect(cardGeisha).toBeHidden();

    // 6. Limpiar búsqueda
    await searchInput.fill('');
    await expect(cardGeisha).toBeVisible();

    // 7. Filtrar por categoría 'tueste'
    const pillTueste = page.locator('.cat-pill[data-category="tueste"]');
    await pillTueste.click();
    const cardAgtron = page.locator('#escala-agtron');
    await expect(cardAgtron).toBeVisible();
    await expect(cardHoney).toBeHidden();

    expect(pageErrors).toHaveLength(0);
  });

  test('la landing page debe exhibir la nueva sección de herramientas destacando el glosario', async ({ page }) => {
    const pageErrors: Error[] = [];
    page.on('pageerror', (err) => pageErrors.push(err));

    await page.goto('/');

    // Verificar el título de la sección de herramientas
    const headingEcosistema = page.getByRole('heading', { name: /Más que un comparador/i });
    await expect(headingEcosistema).toBeVisible();

    // Verificar enlace directo hacia el glosario y herramientas activas
    const linkGlosario = page.locator('a[href="/glosario"]').first();
    await expect(linkGlosario).toBeVisible();

    const linkRecetas = page.locator('a[href="/recetas"]').first();
    await expect(linkRecetas).toBeVisible();

    const linkCalibrador = page.locator('a[href="/calibrador"]').first();
    await expect(linkCalibrador).toBeVisible();

    const linkTiendas = page.locator('a[href="/tiendas"]').first();
    await expect(linkTiendas).toBeVisible();

    expect(pageErrors).toHaveLength(0);
  });
});
