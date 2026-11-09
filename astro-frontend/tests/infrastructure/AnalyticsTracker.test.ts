import { describe, it, expect, beforeEach, vi } from 'vitest';
import { AnalyticsTracker } from '../../src/core/infrastructure/analytics/AnalyticsTracker';

describe('AnalyticsTracker - Enterprise GA4 & GTM Telemetry', () => {
  beforeEach(() => {
    (window as any).dataLayer = [];
    (window as any).gtag = vi.fn();
  });

  it('buildOutboundUrl correctly formats UTM parameters for attribution', () => {
    const baseUrl = 'https://singularcoffee.cl/products/etiopia-yirgacheffe';
    const outboundUrl = AnalyticsTracker.buildOutboundUrl(baseUrl, 'etiopia-yirgacheffe', 'directorio_marcas');

    expect(outboundUrl).toContain('utm_source=cafesitios');
    expect(outboundUrl).toContain('utm_medium=referral');
    expect(outboundUrl).toContain('utm_campaign=directorio_marcas');
    expect(outboundUrl).toContain('utm_content=etiopia-yirgacheffe');
  });

  it('buildOutboundUrl handles URLs with existing query parameters safely', () => {
    const baseUrl = 'https://puelocoffee.cl/shop?variant=123';
    const outboundUrl = AnalyticsTracker.buildOutboundUrl(baseUrl, 'puelo-blend', 'catalogo');

    expect(outboundUrl).toContain('variant=123');
    expect(outboundUrl).toContain('utm_source=cafesitios');
    expect(outboundUrl).toContain('utm_medium=referral');
    expect(outboundUrl).toContain('utm_campaign=catalogo');
    expect(outboundUrl).toContain('utm_content=puelo-blend');
  });

  it('trackClicTiendaExterna pushes ecommerce: null and clic_tienda_externa payload to dataLayer', () => {
    const url = AnalyticsTracker.trackClicTiendaExterna({
      cafeId: 101,
      cafeNombre: 'Geisha Finca El Paraíso',
      tiendaNombre: 'Singular Coffee',
      productoPrecioCLP: 18900,
      formatoGramos: 250,
      precioPorKilo: 75600,
      esEstimado: false,
      destinationUrl: 'https://singularcoffee.cl/geisha'
    });

    expect(url).toContain('utm_source=cafesitios');

    const dataLayer = (window as any).dataLayer;
    expect(dataLayer.length).toBeGreaterThanOrEqual(2);

    // Primer push: reset ecommerce: null
    expect(dataLayer[0]).toEqual({ ecommerce: null });

    // Segundo push: evento de conversión con items y campos en español
    const conversionEvent = dataLayer[1];
    expect(conversionEvent.event).toBe('clic_tienda_externa');
    expect(conversionEvent.tienda_destino).toBe('Singular Coffee');
    expect(conversionEvent.nombre_cafe).toBe('Geisha Finca El Paraíso');
    expect(conversionEvent.precio_clp).toBe(18900);
    expect(conversionEvent.precio_por_kilo).toBe(75600);
    expect(conversionEvent.ecommerce.currency).toBe('CLP');
    expect(conversionEvent.ecommerce.items[0].item_name).toBe('Geisha Finca El Paraíso');
    expect(conversionEvent.ecommerce.items[0].item_brand).toBe('Singular Coffee');
  });

  it('trackViewItemListMarcas pushes view_item_list with brands to dataLayer', () => {
    AnalyticsTracker.trackViewItemListMarcas([
      { id: 1, nombre: 'Singular Coffee' },
      { id: 2, nombre: 'Puelo Coffee' }
    ]);

    const dataLayer = (window as any).dataLayer;
    expect(dataLayer[0]).toEqual({ ecommerce: null });
    expect(dataLayer[1].event).toBe('view_item_list');
    expect(dataLayer[1].item_list_id).toBe('directorio_marcas');
    expect(dataLayer[1].ecommerce.items).toHaveLength(2);
    expect(dataLayer[1].ecommerce.items[0].item_name).toBe('Singular Coffee');
  });

  it('trackSeleccionarMarca pushes seleccionar_marca payload', () => {
    AnalyticsTracker.trackSeleccionarMarca('Artisan Roast', 12, 'tarjeta_directorio');

    const dataLayer = (window as any).dataLayer;
    const evt = dataLayer.find((e: any) => e.event === 'seleccionar_marca');
    expect(evt).toBeDefined();
    expect(evt.tienda_nombre).toBe('Artisan Roast');
    expect(evt.total_cafes_activos).toBe(12);
  });

  it('trackCompararConTienda pushes comparar_con_tienda payload', () => {
    AnalyticsTracker.trackCompararConTienda(42, 'Singular Coffee', 'Puelo Coffee', 1500, 6000);

    const dataLayer = (window as any).dataLayer;
    const evt = dataLayer.find((e: any) => e.event === 'comparar_con_tienda');
    expect(evt).toBeDefined();
    expect(evt.cafe_id).toBe(42);
    expect(evt.tienda_actual).toBe('Singular Coffee');
    expect(evt.tienda_comparada).toBe('Puelo Coffee');
    expect(evt.diferencia_precio_clp).toBe(1500);
    expect(evt.diferencia_precio_kilo).toBe(6000);
  });
});
