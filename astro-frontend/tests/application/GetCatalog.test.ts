import { describe, it, expect, vi } from 'vitest';
import { GetCatalogUseCase } from '../../src/core/application/GetCatalog';
import type { HttpClient } from '../../src/core/infrastructure/api/HttpClient';

describe('GetCatalogUseCase', () => {
  it('transforma parámetros y retorna entidades de dominio CoffeeProduct', async () => {
    const mockHttp = {
      get: vi.fn().mockResolvedValue({
        data: [
          {
            id: 1,
            nombre: 'Café de Prueba',
            tienda: 'Tostaduría X',
            url_detalle: 'https://test.com/cafe',
            variantes: [
              {
                id: 10,
                opcion: 'Grano',
                precio_clp: 12000,
                precio_original_clp: 12000,
                precio_por_kilo: 48000,
                formato_gramos: 250,
                disponible: true,
                en_oferta: false,
                descuento_porcentaje: 0,
                es_estimado: false
              }
            ]
          }
        ],
        total_items: 1
      })
    } as unknown as HttpClient;

    const useCase = new GetCatalogUseCase(mockHttp);
    const result = await useCase.execute({
      searchQuery: 'Bourbon',
      sortBy: 'kilo',
      minPrice: 10000
    });

    expect(mockHttp.get).toHaveBeenCalledWith('/api/v1/products', {
      params: {
        search_query: 'Bourbon',
        store_name: undefined,
        process: undefined,
        country: undefined,
        variety: undefined,
        notes: undefined,
        min_price: 10000,
        max_price: undefined,
        sort_by: 'kilo',
        limit: 30,
        offset: 0,
        category: 'cafe',
        only_available: true
      }
    });

    expect(result.items.length).toBe(1);
    expect(result.items[0].nombre).toBe('Café de Prueba');
    expect(result.items[0].getBestVariant()?.precio_clp).toBe(12000);
  });
});

