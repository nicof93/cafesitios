import { describe, it, expect, vi } from 'vitest';
import { GetWeeklyPriceDropsUseCase } from '../../src/core/application/GetWeeklyPriceDrops';
import type { HttpClient } from '../../src/core/infrastructure/api/HttpClient';

describe('GetWeeklyPriceDropsUseCase', () => {
  it('filtra ofertas con rebaja positiva y descarta variaciones nulas o negativas', async () => {
    const mockHttp = {
      get: vi.fn().mockResolvedValue({
        total: 2,
        dias_evaluados: 7,
        ofertas: [
          {
            oferta_id: 101,
            producto_id: 10,
            nombre_producto: 'Geisha Especial',
            tienda: 'Tostaduría Sur',
            precio_anterior: 12000,
            precio_actual: 9000,
            precio_por_kilo: 36000,
            formato_gramos: 250,
            monto_rebaja: 3000,
            porcentaje_descuento: 25,
            link_detalle: 'https://test.com/geisha'
          },
          {
            oferta_id: 102,
            producto_id: 11,
            nombre_producto: 'Café Inflado Falso',
            tienda: 'Tostaduría Sur',
            precio_anterior: 10000,
            precio_actual: 10000,
            precio_por_kilo: 40000,
            formato_gramos: 250,
            monto_rebaja: 0,
            porcentaje_descuento: 0,
            link_detalle: 'https://test.com/inflado'
          }
        ]
      })
    } as unknown as HttpClient;

    const useCase = new GetWeeklyPriceDropsUseCase(mockHttp);
    const result = await useCase.execute(10, 7);

    expect(mockHttp.get).toHaveBeenCalledWith('/api/v1/products/ofertas-semana', {
      params: { limit: 10, dias: 7 }
    });
    expect(result.length).toBe(1);
    expect(result[0].nombre_producto).toBe('Geisha Especial');
    expect(result[0].monto_rebaja).toBe(3000);
    expect(result[0].porcentaje_descuento).toBe(25);
  });
});
