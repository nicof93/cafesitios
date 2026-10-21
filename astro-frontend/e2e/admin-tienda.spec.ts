import { test, expect } from '@playwright/test';

test.describe('Portal de Administración de Tiendas', () => {
  test('la página de login debe renderizar los campos y controles de seguridad', async ({ page }) => {
    const pageErrors: Error[] = [];
    page.on('pageerror', (err) => pageErrors.push(err));

    await page.goto('/admin-tienda/login');

    // Verificar encabezado del portal
    await expect(page.getByRole('heading', { name: /Portal de Tostadurías/i })).toBeVisible();

    // Campos de credenciales
    const inputEmail = page.locator('#input-email');
    const inputPassword = page.locator('#input-password');
    const checkAntiBot = page.locator('#check-anti-bot');
    const btnSubmit = page.locator('#btn-submit-login');

    await expect(inputEmail).toBeVisible();
    await expect(inputPassword).toBeVisible();
    await expect(checkAntiBot).toBeVisible();
    await expect(btnSubmit).toBeVisible();

    // Modal de primer cambio de contraseña presente en el DOM
    const modalFirstPass = page.locator('#modal-first-change-password');
    await expect(modalFirstPass).toBeAttached();

    // Intentar submit con checkbox bot activo muestra error sin crashear
    await inputEmail.fill('invalido@cafesitios.cl');
    await inputPassword.fill('password123');
    await checkAntiBot.check();
    await btnSubmit.click();

    const alertError = page.locator('#alert-error');
    await expect(alertError).toBeVisible({ timeout: 5000 });

    expect(pageErrors).toHaveLength(0);
  });

  test('el panel de tostaduría debe contar con barra lateral izquierda interactiva', async ({ page }) => {
    // Interceptar consulta a API de perfil para responder 200 con mock
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
          ultima_sincronizacion: new Date().toISOString(),
          estado_sincronizacion: 'exitoso',
        }),
      });
    });

    // Simular sesión autenticada en localStorage
    await page.addInitScript(() => {
      localStorage.setItem('store_admin_token', 'test-token-jwt');
      localStorage.setItem(
        'store_admin_profile',
        JSON.stringify({
          tienda_id: 1,
          tienda_nombre: 'Café Singular Test',
          tienda_url: 'https://singularcoffee.cl',
          usuario_id: 'barista@singular.cl',
          rol: 'STORE_ADMIN',
        })
      );
    });

    await page.goto('/admin-tienda/dashboard');

    // 1. Sidebar lateral izquierdo presente
    const sidebar = page.locator('#main-sidebar');
    await expect(sidebar).toBeAttached();

    // 2. Enlaces principales de navegación vertical en sidebar
    const linkDashboard = sidebar.getByRole('link', { name: /Dashboard/i });
    const linkProductos = sidebar.getByRole('link', { name: /Mis Productos/i });
    const linkRecetas = sidebar.getByRole('link', { name: /Recetas Oficiales/i });
    const linkAuditoria = sidebar.getByRole('link', { name: /Auditoría/i });

    await expect(linkDashboard).toBeAttached();
    await expect(linkProductos).toBeAttached();
    await expect(linkRecetas).toBeAttached();
    await expect(linkAuditoria).toBeAttached();

    // 3. Botón hamburguesa de colapso/expansión de barra lateral
    const btnToggle = page.locator('#sidebar-toggle-btn');
    await expect(btnToggle).toBeVisible();

    // Toggle de colapso
    await btnToggle.click();
    await expect(sidebar).toHaveClass(/sidebar-collapsed|sidebar-open/);

    // 4. Badges de perfil y tienda reflejados
    await expect(page.locator('#header-store-badge')).toHaveText('Café Singular Test');
    await expect(page.locator('#header-user-email')).toHaveText('barista@singular.cl');

    // 5. Opción de Cambiar Contraseña en barra superior y lateral
    const btnOpenPwd = page.locator('#btn-open-change-password');
    const sidebarBtnPwd = page.locator('#sidebar-btn-change-password');
    await expect(btnOpenPwd).toBeVisible();
    await expect(sidebarBtnPwd).toBeAttached();

    // Abrir modal de cambio de contraseña
    await btnOpenPwd.click();
    const modalPwd = page.locator('#modal-change-password');
    await expect(modalPwd).toBeVisible();

    const inputPwdActual = page.locator('#input-pwd-actual');
    const inputPwdNueva = page.locator('#input-pwd-nueva');
    const inputPwdConf = page.locator('#input-pwd-confirmar');
    await expect(inputPwdActual).toBeVisible();
    await expect(inputPwdNueva).toBeVisible();
    await expect(inputPwdConf).toBeVisible();

    // Cerrar modal
    await page.locator('#btn-close-change-password').click();
    await expect(modalPwd).not.toBeVisible();
  });

  test('la vista de recetas oficiales debe cargar y resolver sin colgarse en el spinner', async ({ page }) => {
    const pageErrors: Error[] = [];
    page.on('pageerror', (err) => pageErrors.push(err));

    // Mock de perfil y token en localStorage
    await page.addInitScript(() => {
      localStorage.setItem('store_admin_token', 'test-token-jwt');
      localStorage.setItem(
        'store_admin_profile',
        JSON.stringify({
          tienda_id: 1,
          tienda_nombre: 'Café Singular Test',
          tienda_url: 'https://singularcoffee.cl',
          usuario_id: 'barista@singular.cl',
          rol: 'STORE_ADMIN',
        })
      );
    });

    // Mock de productos para el selector del modal
    await page.route('**/api/v1/admin/tienda/productos*', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          productos: [
            { id: 101, nombre: 'Geisha Los Pozos', precio_por_kilo: 45000 },
          ],
          total: 1,
          page: 1,
          per_page: 100,
        }),
      });
    });

    // Mock de recetas con 1 receta oficial existente
    await page.route('**/api/v1/admin/tienda/recetas', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([
          {
            id: 1,
            producto_id: 101,
            producto_nombre: 'Geisha Los Pozos',
            tienda_id: 1,
            nombre_receta: 'Receta Oficial V60',
            metodo: 'V60',
            dosis_cafe_g: 15.0,
            agua_ml: 250.0,
            ratio: '1:16.7',
            molino_usado: 'Comandante',
            grosor_molienda: 'Media',
            temperatura_c: 92,
            tiempo_total_s: 150,
            notas_catado: 'Notas florales intensas',
            es_borrador: false,
            pasos: ['Preinfusión de 45s con 50g', 'Vertido continuo hasta 250g'],
            fecha_creacion: new Date().toISOString(),
          },
        ]),
      });
    });

    await page.goto('/admin-tienda/recetas');

    // El spinner de carga no debe quedarse pegado indefinidamente
    const loadingSpinner = page.locator('#recipes-loading');
    await expect(loadingSpinner).toBeHidden({ timeout: 5000 });

    // La grilla con la receta oficial debe renderizarse
    const grid = page.locator('#recipes-grid');
    await expect(grid).toBeVisible();
    await expect(grid.getByText('Receta Oficial V60')).toBeVisible();
    await expect(grid.getByText('Geisha Los Pozos')).toBeVisible();

    // Verificar que no ocurrieron errores de sintaxis o runtime de JavaScript en la página
    expect(pageErrors).toHaveLength(0);
  });


  test('el dashboard debe renderizar las secciones de inconsistencias, benchmark, demanda y widget con campos de despacho y tueste', async ({ page }) => {
    const pageErrors: Error[] = [];
    page.on('pageerror', (err) => pageErrors.push(err));

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
          ultima_sincronizacion: new Date().toISOString(),
          estado_sincronizacion: 'exitoso',
          envio_gratis_monto: 30000,
          retiro_en_tienda: true,
          dias_tueste: 'Martes y Jueves',
          fecha_ultimo_tueste: '2026-10-18',
        }),
      });
    });

    await page.route('**/api/v1/admin/tienda/productos/inconsistencias', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          total_inconsistencias: 0,
          inconsistencias: [],
        }),
      });
    });

    await page.route('**/api/v1/admin/tienda/analitica/benchmark', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          precio_kilo_promedio_tienda: 38000.0,
          precio_kilo_promedio_mercado: 40000.0,
          diferencia_porcentaje: -5.0,
          posicion_mercado: 'Competitivo',
          desglose_por_origen: [
            { origen: 'Colombia', precio_kilo_promedio_tienda: 36000, precio_kilo_promedio_mercado: 39000, diferencia_porcentaje: -7.7 }
          ],
        }),
      });
    });

    await page.route('**/api/v1/admin/tienda/analitica/demanda', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          origenes_mas_buscados: [{ origen: 'Etiopía', productos_en_mercado: 24 }],
          oportunidades_catalogo: ['Kenia', 'Guatemala'],
        }),
      });
    });

    await page.addInitScript(() => {
      localStorage.setItem('store_admin_token', 'test-token-jwt');
    });

    await page.goto('/admin-tienda/dashboard');

    // 1. Verificar campos comerciales de perfil
    await expect(page.locator('#prof-envio-gratis')).toBeAttached();
    await expect(page.locator('#prof-retiro-tienda')).toBeAttached();
    await expect(page.locator('#prof-dias-tueste')).toBeAttached();
    await expect(page.locator('#prof-fecha-tueste')).toBeAttached();

    // 2. Verificar sección de inconsistencias
    await expect(page.locator('#inconsistencies-badge')).toBeVisible();

    // 3. Verificar sección de benchmark y demanda
    await expect(page.locator('#bench-store-avg')).toBeVisible();
    await expect(page.locator('#bench-market-avg')).toBeVisible();
    await expect(page.locator('#demand-opportunities-container')).toBeVisible();

    // 4. Verificar widget oficial embebible
    const widgetTextarea = page.locator('#widget-embed-code');
    await expect(widgetTextarea).toBeVisible();
    await expect(widgetTextarea).toHaveValue(/Verificado en Cafesitios/i);

    expect(pageErrors).toHaveLength(0);
  });
});
