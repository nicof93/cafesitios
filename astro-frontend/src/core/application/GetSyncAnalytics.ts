import { HttpClient } from '../infrastructure/api/HttpClient';

export interface SyncPriceChangeDTO {
  id: number;
  variante_id: number;
  nombre: string;
  tienda: string;
  formato_gramos: number;
  formato: string;
  precio_anterior: number;
  precio_nuevo: number;
  precio_actual: number;
  diferencia_clp: number;
  porcentaje_variacion: number;
  precio_kilo_anterior: number;
  precio_kilo_nuevo: number;
  diferencia_kilo_clp: number;
  tipo_cambio: 'SUBIO' | 'BAJO';
  url_detalle: string;
  fecha_cambio?: string | null;
}

export interface SyncNewProductDTO {
  id: number;
  nombre: string;
  tienda: string;
  formato_gramos: number;
  formato: string;
  precio_clp: number;
  precio_por_kilo: number;
  origen?: string | null;
  proceso?: string | null;
  tueste?: string | null;
  url_detalle: string;
  imagen?: string | null;
  fecha_creacion?: string | null;
}

export interface SyncCurrentSummaryDTO {
  fecha_ultima_sincronizacion?: string | null;
  ultima_sincronizacion?: string | null;
  estado: string;
  total_nuevos: number;
  total_subieron_precio: number;
  total_bajaron_precio: number;
  total_cambios_precio: number;
  porcentaje_variacion_global: number;
  ahorro_total_clp: number;
  porcentaje_ahorro_promedio: number;
  total_ofertas_monitoreadas: number;
  total_productos_catalogados: number;
  productos_nuevos: SyncNewProductDTO[];
  cambios_precio: SyncPriceChangeDTO[];
}

export interface SyncHistoryLogDTO {
  id: number;
  fecha_ejecucion: string;
  fecha: string;
  hora: string;
  duracion_estimada_segundos: number;
  duracion_estimada: string;
  estado: string;
  productos_nuevos: number;
  productos_actualizados: number;
  productos_con_cambio_precio: number;
  mensaje_error?: string | null;
}

export interface PaginatedSyncHistoryDTO {
  page: number;
  page_size: number;
  total_items: number;
  total_pages: number;
  items: SyncHistoryLogDTO[];
}

export interface MarketStoreDiscountDTO {
  nombre?: string | null;
  descuento_promedio_porcentaje: number;
  total_ofertas_descuento: number;
  precio_promedio_kilo: number;
  cantidad_productos: number;
}

export interface MarketDistributionDTO {
  categoria: string;
  cantidad: number;
  porcentaje: number;
  precio_promedio_kilo: number;
}

export interface MarketAnalyticsDTO {
  precio_promedio_kilo: number;
  precio_minimo_kilo: number;
  precio_maximo_kilo: number;
  precio_promedio_bolsa_clp: number;
  total_variantes_analizadas: number;
  total_tiendas_activas: number;
  tienda_mejor_descuento: MarketStoreDiscountDTO;
  tiendas_mas_competitivas: MarketStoreDiscountDTO[];
  distribucion_tueste: MarketDistributionDTO[];
  distribucion_proceso: MarketDistributionDTO[];
}

export class GetSyncAnalyticsUseCase {
  private readonly httpClient: HttpClient;

  constructor(httpClient?: HttpClient) {
    this.httpClient = httpClient || new HttpClient();
  }

  async getCurrentSummary(): Promise<SyncCurrentSummaryDTO> {
    return this.httpClient.get<SyncCurrentSummaryDTO>('/api/sincronizaciones/resumen-actual', { timeoutMs: 8000 });
  }

  async getHistory(page = 1, pageSize = 10): Promise<PaginatedSyncHistoryDTO> {
    return this.httpClient.get<PaginatedSyncHistoryDTO>('/api/sincronizaciones/historial', {
      params: { page, page_size: pageSize },
      timeoutMs: 8000,
    });
  }

  async getMarketAnalytics(): Promise<MarketAnalyticsDTO> {
    return this.httpClient.get<MarketAnalyticsDTO>('/api/analitica/mercado', { timeoutMs: 8000 });
  }
}
