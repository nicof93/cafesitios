import { ProductVariant, type ProductVariantProps } from './ProductVariant';

export interface ProductRecipe {
  id: number;
  nombre_receta: string;
  metodo: string;
  dosis_cafe_g: number;
  agua_ml: number;
  ratio?: string;
  molino_usado?: string;
  grosor_molienda?: string;
  temperatura_c?: number;
  tiempo_total_s?: number;
  notas_catado?: string;
  pasos?: string[];
  es_borrador?: boolean;
  autor_tipo?: string;
  tienda_nombre?: string;
  fecha_creacion?: string;
}

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
  atributos_organolepticos?: Record<string, number>;
  variantes_por_gramaje?: any[];
  descripcion?: string;
  descripcion_resumida?: string;
  resumen_corto?: string;
  fecha_actualizacion?: string;
  tienda_id?: number;
  tienda_telefono_whatsapp?: string;
  recetas?: ProductRecipe[];
  oculto_catalogo?: boolean;
}

export class CoffeeProduct {
  readonly id: number;
  readonly nombre: string;
  readonly tienda: string;
  readonly tienda_id?: number;
  readonly tienda_telefono_whatsapp?: string;
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
  readonly atributos_organolepticos?: Record<string, number>;
  readonly descripcion?: string;
  readonly descripcion_resumida?: string;
  readonly resumen_corto?: string;
  readonly fecha_actualizacion?: string;
  readonly recetas: ProductRecipe[];
  readonly oculto_catalogo: boolean;

  constructor(props: CoffeeProductProps) {
    this.id = props.id;
    this.nombre = props.nombre;
    this.tienda = props.tienda;
    this.tienda_id = props.tienda_id;
    this.tienda_telefono_whatsapp = props.tienda_telefono_whatsapp;
    this.url_detalle = props.url_detalle;
    this.imagen = props.imagen || 'https://images.unsplash.com/photo-1559056199-641a0ac8b55e?q=80&w=400&auto=format&fit=crop';
    this.categoria = props.categoria || 'cafe';
    this.recetas = props.recetas || [];
    this.oculto_catalogo = Boolean(props.oculto_catalogo);

    
    // Normalizar variantes (acepta array o variante única en listados o variantes_por_gramaje)
    const rawVars = props.variantes || props.variantes_por_gramaje;
    if (rawVars && rawVars.length > 0) {
      this.variantes = rawVars.map(v => new ProductVariant(v));
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
    this.atributos_organolepticos = props.atributos_organolepticos;
    this.descripcion = props.descripcion;
    const descRes = props.descripcion_resumida || props.resumen_corto || (props as any).caracteristicas_fuente?.resumen_corto;
    this.descripcion_resumida = descRes ? String(descRes).trim() : undefined;
    this.resumen_corto = this.descripcion_resumida;
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

