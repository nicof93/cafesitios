import { Store, type StoreProps } from '../domain/models/Store';
import { HttpClient } from '../infrastructure/api/HttpClient';

export interface GetStoresParams {
  page?: number;
  pageSize?: number;
  sortBy?: 'product_count_desc' | 'distance_asc' | 'name_asc';
  lat?: number;
  lon?: number;
}

interface RawStoresResponse {
  items: StoreProps[];
  total: number;
}

export class GetStoresUseCase {
  constructor(private readonly http: HttpClient = new HttpClient()) {}

  async execute(params: GetStoresParams = {}): Promise<Store[]> {
    const queryParams: Record<string, string | number | undefined> = {
      page: params.page || 1,
      page_size: params.pageSize || 50,
      sort_by: params.sortBy || 'product_count_desc',
      lat: params.lat,
      lon: params.lon
    };

    const response = await this.http.get<RawStoresResponse>('/api/v1/stores', {
      params: queryParams
    });

    return (response.items || []).map(s => new Store(s));
  }
}

