import { HttpClient } from '../infrastructure/api/HttpClient';

export interface WeeklyPriceDropDTO {
  oferta_id: number;
  producto_id: number;
  nombre_producto: string;
  tienda: string;
  url_tienda?: string;
  imagen_url?: string;
  formato_gramos: number;
  precio_anterior: number;
  precio_actual: number;
  precio_por_kilo: number;
  monto_rebaja: number;
  porcentaje_descuento: number;
  link_detalle: string;
  fecha_cambio?: string;
}

export interface WeeklyPriceDropsResponseDTO {
  total: number;
  dias_evaluados: number;
  ofertas: WeeklyPriceDropDTO[];
}

export class GetWeeklyPriceDropsUseCase {
  constructor(private readonly http: HttpClient = new HttpClient()) {}

  async execute(limit: number = 10, dias: number = 7): Promise<WeeklyPriceDropDTO[]> {
    const res = await this.http.get<WeeklyPriceDropsResponseDTO>('/api/v1/products/ofertas-semana', {
      params: { limit, dias }
    });
    return (res?.ofertas || []).filter(o => o.monto_rebaja > 0 && o.precio_actual < o.precio_anterior);
  }
}
