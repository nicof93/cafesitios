import { CoffeeProduct, type CoffeeProductProps } from '../domain/models/CoffeeProduct';
import { HttpClient } from '../infrastructure/api/HttpClient';

export interface CompareResult {
  productos: CoffeeProduct[];
  total: number;
}

interface RawCompareResponse {
  productos: CoffeeProductProps[];
  total: number;
}

export class CompareProductsUseCase {
  constructor(private readonly http: HttpClient = new HttpClient()) {}

  async execute(productIds: number[]): Promise<CompareResult> {
    if (productIds.length === 0) {
      return { productos: [], total: 0 };
    }

    const idsParam = productIds.slice(0, 4).join(',');
    const response = await this.http.get<RawCompareResponse>('/api/v1/products/compare', {
      params: { ids: idsParam }
    });

    const productos = (response.productos || [])
      .filter((p: any) => !p.oculto_catalogo)
      .map(p => new CoffeeProduct(p));
    return {
      productos,
      total: response.total || productos.length
    };
  }
}

