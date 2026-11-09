import { HttpClient } from '../infrastructure/api/HttpClient';

export interface StorePublicDetailData {
  id: number;
  nombre: string;
  slug: string;
  url_base?: string;
  sitio_oficial?: string;
  logo_url?: string;
  descripcion?: string;
  comuna?: string;
  direccion?: string;
  latitud?: number;
  longitud?: number;
  telefono_whatsapp?: string;
  instagram_url?: string;
  envio_gratis_monto?: number;
  retiro_en_tienda: boolean;
  dias_tueste?: string;
  fecha_ultimo_tueste?: string;
  servicios: string[];
  carta_comida_url?: string;
  carta_comida_tamano_bytes?: number;
  cantidad_productos: number;
  sucursales: Array<{
    id: number;
    nombre: string;
    direccion?: string;
    comuna?: string;
    region?: string;
    latitud?: number;
    longitud?: number;
  }>;
  cafes_populares: Array<{
    id: number;
    nombre: string;
    marca: string;
    formato_gramos?: number;
    precio_clp?: number;
    precio_por_kilo?: number;
    en_oferta: boolean;
    imagen_url?: string;
    url_origen?: string;
    origen?: string;
    tipo_tueste?: string;
  }>;
  novedades: Array<{
    id: number;
    titulo: string;
    descripcion: string;
    link_url?: string;
    imagen_url?: string;
    categoria_tipo?: string;
    fecha_creacion: string;
  }>;
  productos: Array<{
    id: number;
    nombre: string;
    marca: string;
    formato_gramos?: number;
    precio_clp?: number;
    precio_por_kilo?: number;
    en_oferta: boolean;
    imagen_url?: string;
    url_origen?: string;
    origen?: string;
    tipo_tueste?: string;
  }>;
}

export class GetStoreDetailUseCase {
  constructor(private readonly http: HttpClient = new HttpClient()) {}

  async execute(slugOrId: string): Promise<StorePublicDetailData | null> {
    try {
      return await this.http.get<StorePublicDetailData>(`/api/v1/tiendas/${encodeURIComponent(slugOrId)}/detalle-publico`);
    } catch {
      return null;
    }
  }
}
