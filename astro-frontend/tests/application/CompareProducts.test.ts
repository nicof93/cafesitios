import { describe, it, expect, vi } from 'vitest';
import { CompareProductsUseCase } from '../../src/core/application/CompareProducts';
import type { HttpClient } from '../../src/core/infrastructure/api/HttpClient';

describe('CompareProductsUseCase (CU-03)', () => {
  it('limita a un máximo de 4 productos y consulta el endpoint de comparación', async () => {
    const mockHttp = {
      get: vi.fn().mockResolvedValue({
        productos: [
          {
            id: 1,
            nombre: 'Café A',
            tienda: 'Tienda 1',
            url_detalle: 'https://tienda1.cl',
            variantes: [{ id: 10, precio_clp: 10000, precio_por_kilo: 40000, formato_gramos: 250, disponible: true }]
          },
          {
            id: 2,
            nombre: 'Café B',
            tienda: 'Tienda 2',
            url_detalle: 'https://tienda2.cl',
            variantes: [{ id: 20, precio_clp: 12000, precio_por_kilo: 48000, formato_gramos: 250, disponible: true }]
          }
        ],
        total: 2
      })
    } as unknown as HttpClient;

    const useCase = new CompareProductsUseCase(mockHttp);
    // Enviar 6 IDs para verificar que solo se toman los primeros 4
    const result = await useCase.execute([1, 2, 3, 4, 5, 6]);

    expect(mockHttp.get).toHaveBeenCalledWith('/api/v1/products/compare', {
      params: { ids: '1,2,3,4' }
    });

    expect(result.productos.length).toBe(2);
    expect(result.productos[0].nombre).toBe('Café A');
  });

  it('retorna arreglo vacío si no se proporcionan IDs', async () => {
    const mockHttp = { get: vi.fn() } as unknown as HttpClient;
    const useCase = new CompareProductsUseCase(mockHttp);
    const result = await useCase.execute([]);

    expect(mockHttp.get).not.toHaveBeenCalled();
    expect(result.productos.length).toBe(0);
  });
});

