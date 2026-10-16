import { describe, it, expect, vi } from 'vitest';
import { GetStoresUseCase } from '../../src/core/application/GetStores';
import type { HttpClient } from '../../src/core/infrastructure/api/HttpClient';

describe('GetStoresUseCase', () => {
  it('envía sortBy name_asc para listar tostadurías en orden alfabético', async () => {
    const mockHttp = {
      get: vi.fn().mockResolvedValue({
        items: [
          {
            nombre: 'Altocielo Coffee',
            url_base: 'https://altocielo.cl',
            cantidad_productos: 12
          },
          {
            nombre: 'Singular Coffee',
            url_base: 'https://singularcoffee.cl',
            cantidad_productos: 24
          }
        ],
        total: 2
      })
    } as unknown as HttpClient;

    const useCase = new GetStoresUseCase(mockHttp);
    const stores = await useCase.execute({
      pageSize: 50,
      sortBy: 'name_asc'
    });

    expect(mockHttp.get).toHaveBeenCalledWith('/api/v1/stores', {
      params: {
        page: 1,
        page_size: 50,
        sort_by: 'name_asc',
        lat: undefined,
        lon: undefined
      }
    });

    expect(stores.length).toBe(2);
    expect(stores[0].nombre).toBe('Altocielo Coffee');
    expect(stores[1].nombre).toBe('Singular Coffee');
  });
});

