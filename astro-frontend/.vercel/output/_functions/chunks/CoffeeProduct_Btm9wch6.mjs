class ProductVariant {
  id;
  opcion;
  precio_clp;
  precio_original_clp;
  precio_por_kilo;
  formato_gramos;
  disponible;
  en_oferta;
  descuento_porcentaje;
  es_estimado;
  sku;
  historial_precios;
  constructor(props) {
    this.id = props.id;
    this.opcion = props.opcion || "Único";
    this.precio_clp = Math.max(0, Math.floor(props.precio_clp || 0));
    this.precio_original_clp = Math.max(0, Math.floor(props.precio_original_clp || props.precio_clp || 0));
    this.formato_gramos = props.formato_gramos > 0 ? props.formato_gramos : 250;
    this.es_estimado = Boolean(props.es_estimado);
    this.precio_por_kilo = props.precio_por_kilo > 0 ? props.precio_por_kilo : ProductVariant.calcularPrecioPorKilo(this.precio_clp, this.formato_gramos);
    this.disponible = Boolean(props.disponible);
    this.en_oferta = Boolean(props.en_oferta || this.precio_original_clp > this.precio_clp);
    this.descuento_porcentaje = props.descuento_porcentaje > 0 ? props.descuento_porcentaje : this.en_oferta && this.precio_original_clp > 0 ? Math.round((this.precio_original_clp - this.precio_clp) / this.precio_original_clp * 100) : 0;
    this.sku = props.sku;
    this.historial_precios = props.historial_precios || [];
  }
  static calcularPrecioPorKilo(precioClp, formatoGramos) {
    if (precioClp <= 0 || formatoGramos <= 0) return 0;
    return Math.round(precioClp / formatoGramos * 1e3);
  }
  isFree() {
    return this.precio_clp === 0;
  }
}

class CoffeeProduct {
  id;
  nombre;
  tienda;
  url_detalle;
  imagen;
  categoria;
  variantes;
  origen;
  proceso;
  variedad;
  notas_cata;
  tueste;
  escala_agtron;
  altura_msnm;
  puntuacion_sca;
  descripcion;
  fecha_actualizacion;
  constructor(props) {
    this.id = props.id;
    this.nombre = props.nombre;
    this.tienda = props.tienda;
    this.url_detalle = props.url_detalle;
    this.imagen = props.imagen || "https://images.unsplash.com/photo-1559056199-641a0ac8b55e?q=80&w=400&auto=format&fit=crop";
    this.categoria = props.categoria || "cafe";
    if (props.variantes && props.variantes.length > 0) {
      this.variantes = props.variantes.map((v) => new ProductVariant(v));
    } else if (props.variante) {
      this.variantes = [new ProductVariant(props.variante)];
    } else {
      this.variantes = [];
    }
    this.tienda = (props.tienda || "").replace(/\)+$/, "").trim();
    this.origen = props.origen || props.pais_origen;
    this.proceso = props.proceso;
    this.variedad = props.variedad;
    if (Array.isArray(props.notas_cata)) {
      this.notas_cata = props.notas_cata.map((n) => {
        if (typeof n === "string") return n.trim();
        if (n && typeof n === "object") {
          return String(n.nombre || n.clave_normalizada || "").trim();
        }
        return String(n).trim();
      }).filter(Boolean);
    } else {
      this.notas_cata = [];
    }
    this.tueste = props.tueste;
    this.escala_agtron = props.escala_agtron;
    const minAlt = props.elevacion_min_msnm;
    const maxAlt = props.elevacion_max_msnm;
    this.altura_msnm = props.altura_msnm || (minAlt ? maxAlt ? `${minAlt} - ${maxAlt} msnm` : `${minAlt} msnm` : void 0);
    this.puntuacion_sca = props.puntuacion_sca;
    this.descripcion = props.descripcion;
    this.fecha_actualizacion = props.fecha_actualizacion;
  }
  /**
   * Obtiene la variante principal o más económica por kilo.
   */
  getBestVariant(onlyAvailable = true) {
    if (this.variantes.length === 0) return void 0;
    const candidatas = onlyAvailable ? this.variantes.filter((v) => v.disponible) : this.variantes;
    const pool = candidatas.length > 0 ? candidatas : this.variantes;
    return [...pool].sort((a, b) => a.precio_por_kilo - b.precio_por_kilo)[0];
  }
  hasAvailableVariants() {
    return this.variantes.some((v) => v.disponible);
  }
  isFreeSample() {
    const best = this.getBestVariant(false);
    return Boolean(best && best.isFree());
  }
}

export { CoffeeProduct as C };
