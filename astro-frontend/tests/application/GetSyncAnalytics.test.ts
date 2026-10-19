import { describe, it, expect, vi } from 'vitest';
import { GetSyncAnalyticsUseCase } from '../../src/core/application/GetSyncAnalytics';
import type { HttpClient } from '../../src/core/infrastructure/api/HttpClient';

describe('GetSyncAnalyticsUseCase', () => {
  it('obtiene el resumen actual, historial paginado y analítica de mercado', async () => {
    const mockHttp = {
      get: vi.fn()
        .mockResolvedValueOnce({
          estado: 'OK',
          total_nuevos: 2,
          total_subieron_precio: 1,
          total_bajaron_precio: 3,
          porcentaje_variacion_global: -4.2,
          ahorro_total_clp: 4500,
          porcentaje_ahorro_promedio: 15.0,
          total_ofertas_monitoreadas: 42,
          total_productos_catalogados: 30,
          productos_nuevos: [],
          cambios_precio: []
        })
        .mockResolvedValueOnce({
          page: 1,
          page_size: 10,
          total_items: 1,
          total_pages: 1,
          items: [
            {
              id: 1,
              fecha_ejecucion: '2026-10-16T03:30:00Z',
              fecha: '2026-10-16',
              hora: '03:30:00',
              duracion_estimada_segundos: 12.4,
              duracion_estimada: '12.4s',
              estado: 'OK',
              productos_nuevos: 2,
              productos_actualizados: 10,
              productos_con_cambio_precio: 4
            }
          ]
        })
        .mockResolvedValueOnce({
          precio_promedio_kilo: 41200,
          precio_minimo_kilo: 32000,
          precio_maximo_kilo: 68000,
          precio_promedio_bolsa_clp: 10300,
          total_variantes_analizadas: 42,
          total_tiendas_activas: 5,
          tienda_mejor_descuento: {
            nombre: 'Singular Coffee',
            descuento_promedio_porcentaje: 20,
            total_ofertas_descuento: 3,
            precio_promedio_kilo: 38000,
            cantidad_productos: 12
          },
          tiendas_mas_competitivas: [],
          distribucion_tueste: [],
          distribucion_proceso: []
        })
    } as unknown as HttpClient;

    const useCase = new GetSyncAnalyticsUseCase(mockHttp);

    const summary = await useCase.getCurrentSummary();
    const history = await useCase.getHistory(1, 10);
    const market = await useCase.getMarketAnalytics();

    expect(mockHttp.get).toHaveBeenNthCalledWith(1, '/api/sincronizaciones/resumen-actual', { timeoutMs: 8000 });
    expect(mockHttp.get).toHaveBeenNthCalledWith(2, '/api/sincronizaciones/historial', {
      params: { page: 1, page_size: 10 },
      timeoutMs: 8000
    });
    expect(mockHttp.get).toHaveBeenNthCalledWith(3, '/api/analitica/mercado', { timeoutMs: 8000 });

    expect(summary.total_bajaron_precio).toBe(3);
    expect(history.items[0].estado).toBe('OK');
    expect(market.tienda_mejor_descuento.nombre).toBe('Singular Coffee');
  });
});
