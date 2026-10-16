import { ProductVariant, type ProductVariantProps } from './ProductVariant';

export interface CoffeeProductProps {
  id: number;
  nombre: string;
  tienda: string;
  url_detalle: string;
  imagen?: string;
  categoria?: string;
  variantes?: ProductVariantProps[];
  variante?: ProductVariantProps; // Para respuestas planas de listado
  origen?: string;
  proceso?: string;
  variedad?: string;
  notas_cata?: any[];
  tueste?: string;
  escala_agtron?: number;
  altura_msnm?: string;
  puntuacion_sca?: number;
  descripcion?: string;
  fecha_actualizacion?: string;
}

export class CoffeeProduct {
  readonly id: number;
  readonly nombre: string;
  readonly tienda: string;
  readonly url_detalle: string;
  readonly imagen: string;
  readonly categoria: string;
  readonly variantes: ProductVariant[];
  readonly origen?: string;
  readonly proceso?: string;
  readonly variedad?: string;
  readonly notas_cata: string[];
  readonly tueste?: string;
  readonly escala_agtron?: number;
  readonly altura_msnm?: string;
  readonly puntuacion_sca?: number;
  readonly descripcion?: string;
  readonly fecha_actualizacion?: string;

  constructor(props: CoffeeProductProps) {
    this.id = props.id;
    this.nombre = props.nombre;
    this.tienda = props.tienda;
    this.url_detalle = props.url_detalle;
    this.imagen = props.imagen || 'https://images.unsplash.com/photo-1559056199-641a0ac8b55e?q=80&w=400&auto=format&fit=crop';
    this.categoria = props.categoria || 'cafe';

    
    // Normalizar variantes (acepta array o variante única en listados)
    if (props.variantes && props.variantes.length > 0) {
      this.variantes = props.variantes.map(v => new ProductVariant(v));
    } else if (props.variante) {
      this.variantes = [new ProductVariant(props.variante)];
    } else {
      this.variantes = [];
    }

    this.tienda = (props.tienda || '').replace(/\)+$/, '').trim();
    this.origen = props.origen || (props as any).pais_origen;
    this.proceso = props.proceso;
    this.variedad = props.variedad;
    
    // Normalizar notas_cata defensivamente (soporta strings u objetos devueltos por la API de detalle)
    if (Array.isArray(props.notas_cata)) {
      this.notas_cata = props.notas_cata.map(n => {
        if (typeof n === 'string') return n.trim();
        if (n && typeof n === 'object') {
          return String(n.nombre || n.clave_normalizada || '').trim();
        }
        return String(n).trim();
      }).filter(Boolean);
    } else {
      this.notas_cata = [];
    }
    this.tueste = props.tueste;
    this.escala_agtron = props.escala_agtron;
    const minAlt = (props as any).elevacion_min_msnm;
    const maxAlt = (props as any).elevacion_max_msnm;
    this.altura_msnm = props.altura_msnm || (minAlt ? (maxAlt ? `${minAlt} - ${maxAlt} msnm` : `${minAlt} msnm`) : undefined);
    this.puntuacion_sca = props.puntuacion_sca;
    this.descripcion = props.descripcion;
    this.fecha_actualizacion = props.fecha_actualizacion;
  }

  /**
   * Obtiene la variante principal o más económica por kilo.
   */
  getBestVariant(onlyAvailable: boolean = true): ProductVariant | undefined {
    if (this.variantes.length === 0) return undefined;
    const candidatas = onlyAvailable
      ? this.variantes.filter(v => v.disponible)
      : this.variantes;
    
    const pool = candidatas.length > 0 ? candidatas : this.variantes;
    return [...pool].sort((a, b) => a.precio_por_kilo - b.precio_por_kilo)[0];
  }

  hasAvailableVariants(): boolean {
    return this.variantes.some(v => v.disponible);
  }

  isFreeSample(): boolean {
    const best = this.getBestVariant(false);
    return Boolean(best && best.isFree());
  }
}

