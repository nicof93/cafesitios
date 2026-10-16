import { CoffeeProduct, type CoffeeProductProps } from '../domain/models/CoffeeProduct';
import { HttpClient } from '../infrastructure/api/HttpClient';

export interface ProductDetailResult {
  product: CoffeeProduct;
  matches: CoffeeProduct[];
}

interface RawMatchesResponse {
  coincidencias: CoffeeProductProps[];
  total: number;
}

export class GetProductDetailUseCase {
  constructor(private readonly http: HttpClient = new HttpClient()) {}

  async execute(productId: number | string): Promise<ProductDetailResult> {
    const productData = await this.http.get<CoffeeProductProps>(`/api/v1/products/${productId}/detail`);
    const product = new CoffeeProduct(productData);

    let matches: CoffeeProduct[] = [];
    try {
      const matchesData = await this.http.get<RawMatchesResponse>(`/api/v1/products/${productId}/matches`);
      matches = (matchesData.coincidencias || []).map(m => new CoffeeProduct(m));
    } catch {
      // Si falla la búsqueda de sustitutos, no bloquea el detalle principal
    }

    return { product, matches };
  }
}

