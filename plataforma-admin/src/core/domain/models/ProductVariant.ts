export interface PriceHistoryPoint {
  id?: number;
  precio_clp: number;
  precio_original_clp?: number;
  precio_por_kilo: number;
  fecha_registro: string;
}

export interface ProductVariantProps {
  id: number;
  opcion: string;
  precio_clp: number;
  precio_original_clp: number;
  precio_por_kilo: number;
  formato_gramos: number;
  disponible: boolean;
  en_oferta: boolean;
  descuento_porcentaje: number;
  es_estimado: boolean;
  sku?: string;
  historial_precios?: PriceHistoryPoint[];
}

export class ProductVariant {
  readonly id: number;
  readonly opcion: string;
  readonly precio_clp: number;
  readonly precio_original_clp: number;
  readonly precio_por_kilo: number;
  readonly formato_gramos: number;
  readonly disponible: boolean;
  readonly en_oferta: boolean;
  readonly descuento_porcentaje: number;
  readonly es_estimado: boolean;
  readonly sku?: string;
  readonly historial_precios: PriceHistoryPoint[];

  constructor(props: ProductVariantProps) {
    this.id = props.id;
    this.opcion = props.opcion || 'Único';
    this.precio_clp = Math.max(0, Math.floor(props.precio_clp || 0));
    this.precio_original_clp = Math.max(0, Math.floor(props.precio_original_clp || props.precio_clp || 0));
    this.formato_gramos = props.formato_gramos > 0 ? props.formato_gramos : 250;
    this.es_estimado = Boolean(props.es_estimado);
    this.precio_por_kilo = props.precio_por_kilo > 0
      ? props.precio_por_kilo
      : ProductVariant.calcularPrecioPorKilo(this.precio_clp, this.formato_gramos);
    this.disponible = Boolean(props.disponible);
    this.en_oferta = Boolean(props.en_oferta || (this.precio_original_clp > this.precio_clp));
    this.descuento_porcentaje = props.descuento_porcentaje > 0
      ? props.descuento_porcentaje
      : (this.en_oferta && this.precio_original_clp > 0
          ? Math.round(((this.precio_original_clp - this.precio_clp) / this.precio_original_clp) * 100)
          : 0);
    this.sku = props.sku;
    this.historial_precios = props.historial_precios || [];
  }

  static calcularPrecioPorKilo(precioClp: number, formatoGramos: number): number {
    if (precioClp <= 0 || formatoGramos <= 0) return 0;
    return Math.round((precioClp / formatoGramos) * 1000);
  }

  isFree(): boolean {
    return this.precio_clp === 0;
  }
}

