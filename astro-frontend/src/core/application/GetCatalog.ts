import { CoffeeProduct, type CoffeeProductProps } from '../domain/models/CoffeeProduct';
import { HttpClient } from '../infrastructure/api/HttpClient';

export interface CatalogFilterParams {
  searchQuery?: string;
  storeName?: string;
  process?: string;
  country?: string;
  variety?: string;
  notes?: string;
  minPrice?: number;
  maxPrice?: number;
  sortBy?: 'kilo' | 'unit' | 'created_desc';
  page?: number;
  limit?: number;
  offset?: number;
  category?: string;
  onlyAvailable?: boolean;
}

export interface CatalogResult {
  items: CoffeeProduct[];
  total: number;
}

interface RawCatalogResponse {
  data: CoffeeProductProps[];
  total_items: number;
  page?: number;
  limit?: number;
  offset?: number;
}

export class GetCatalogUseCase {
  constructor(private readonly http: HttpClient = new HttpClient()) {}

  async execute(params: CatalogFilterParams = {}): Promise<CatalogResult> {
    const queryParams: Record<string, string | number | boolean | undefined> = {
      search_query: params.searchQuery,
      store_name: params.storeName,
      process: params.process,
      country: params.country,
      variety: params.variety,
      notes: params.notes,
      min_price: params.minPrice,
      max_price: params.maxPrice,
      sort_by: params.sortBy || 'kilo',
      limit: params.limit || 30,
      offset: params.offset || 0,
      category: params.category !== undefined ? params.category : 'cafe',
      only_available: params.onlyAvailable !== undefined ? params.onlyAvailable : true
    };


    const response = await this.http.get<RawCatalogResponse>('/api/v1/products', {
      params: queryParams
    });

    const items = (response.data || []).map(p => new CoffeeProduct(p));
    return {
      items,
      total: response.total_items || items.length
    };
  }
}

