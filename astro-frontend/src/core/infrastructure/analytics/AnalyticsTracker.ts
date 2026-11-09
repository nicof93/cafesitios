import { Environment } from '../config/Environment';

declare global {
  interface Window {
    dataLayer?: unknown[];
    gtag?: (...args: unknown[]) => void;
  }
}

export interface ClicTiendaExternaPayload {
  cafeId?: number | string;
  cafeNombre?: string;
  tiendaNombre: string;
  productoPrecioCLP?: number;
  formatoGramos?: number;
  precioPorKilo?: number;
  esEstimado?: boolean;
  destinationUrl: string;
  productSlug?: string;
  campaign?: string;
}

export class AnalyticsTracker {
  /**
   * Generador automatizado de URLs con parámetros UTM para atribución a marcas.
   * Regla de Negocio: ?utm_source=cafesitios&utm_medium=referral&utm_campaign=directorio_marcas&utm_content={producto_slug}
   */
  static buildOutboundUrl(
    baseUrl: string,
    productSlug?: string,
    campaign: string = 'directorio_marcas'
  ): string {
    if (!baseUrl || !baseUrl.trim()) return '#';
    try {
      const url = new URL(baseUrl.trim().startsWith('http') ? baseUrl.trim() : `https://${baseUrl.trim()}`);
      url.searchParams.set('utm_source', 'cafesitios');
      url.searchParams.set('utm_medium', 'referral');
      url.searchParams.set('utm_campaign', campaign);
      url.searchParams.set('utm_content', productSlug ? productSlug.replace(/\s+/g, '-').toLowerCase() : 'visita_tienda');
      return url.toString();
    } catch {
      const sep = baseUrl.includes('?') ? '&' : '?';
      const slugVal = productSlug ? encodeURIComponent(productSlug.replace(/\s+/g, '-').toLowerCase()) : 'visita_tienda';
      return `${baseUrl}${sep}utm_source=cafesitios&utm_medium=referral&utm_campaign=${encodeURIComponent(campaign)}&utm_content=${slugVal}`;
    }
  }

  private static sendToDataLayer(eventName: string, params: Record<string, unknown> = {}): void {
    if (typeof window === 'undefined') return;

    // Google Analytics (gtag)
    if (typeof window.gtag === 'function') {
      window.gtag('event', eventName, params);
    }

    // Google Tag Manager (dataLayer)
    window.dataLayer = window.dataLayer || [];
    window.dataLayer.push({
      event: eventName,
      ...params
    });

    // Envío asíncrono al backend para métricas sin cookies (Costo $0 USD)
    this.sendBeacon(eventName, params);
  }

  private static sendBeacon(eventType: string, metadata: Record<string, unknown> = {}): void {
    if (typeof window === 'undefined') return;
    if (typeof process !== 'undefined' && (process.env.NODE_ENV === 'test' || process.env.VITEST)) return;

    try {
      const url = `${Environment.getApiBaseUrl()}/api/v1/telemetry/event`;
      const rawProdId = metadata.product_id || metadata.item_id || metadata.productId || metadata.cafe_id;
      const productId = rawProdId ? Number(rawProdId) : undefined;
      const rawVarId = metadata.variant_id || metadata.variante_id;
      const varianteId = rawVarId ? Number(rawVarId) : undefined;

      const payload = JSON.stringify({
        tipo_evento: eventType,
        producto_id: Number.isFinite(productId) ? productId : undefined,
        variante_id: Number.isFinite(varianteId) ? varianteId : undefined,
        metadata_evento: metadata,
        event_type: eventType,
        metadata
      });
      if (typeof fetch === 'function') {
        fetch(url, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: payload,
          keepalive: true
        }).catch(() => {
          if (navigator.sendBeacon) {
            navigator.sendBeacon(url, new Blob([payload], { type: 'application/json' }));
          }
        });
      } else if (navigator.sendBeacon) {
        navigator.sendBeacon(url, new Blob([payload], { type: 'application/json' }));
      }
    } catch {
      // Ignorar errores en segundo plano
    }
  }

  // --- TELEMETRÍA ENTERPRISE GA4 & GTM DATALAYER v2 (SECCIÓN 4) ---

  /**
   * Intención de Compra Saliente (Conversión Primaria - clic_tienda_externa).
   * Emite dualidad: estándar GA4 e-commerce (items) + parámetros de negocio en español.
   * Retorna la URL destino enriquecida con UTMs.
   */
  static trackClicTiendaExterna(payload: ClicTiendaExternaPayload): string {
    const cafeNombre = payload.cafeNombre || 'Café de Especialidad';
    const tiendaNombre = payload.tiendaNombre || 'Tostaduría Asociada';
    const precioCLP = Number(payload.productoPrecioCLP) || 0;
    const formatoGramos = Number(payload.formatoGramos) || 250;
    const precioPorKilo = Number(payload.precioPorKilo) || (formatoGramos > 0 ? Math.round((precioCLP / formatoGramos) * 1000) : 0);
    const cafeId = payload.cafeId ? String(payload.cafeId) : '0';

    const urlConUTM = this.buildOutboundUrl(
      payload.destinationUrl,
      payload.productSlug || cafeNombre,
      payload.campaign || 'directorio_marcas'
    );

    if (typeof window !== 'undefined') {
      window.dataLayer = window.dataLayer || [];
      // 1. Resetear contexto previo de comercio electrónico para evitar contaminación entre SPA/islas
      window.dataLayer.push({ ecommerce: null });

      // 2. Disparar conversión GA4 E-commerce + parámetros en español
      window.dataLayer.push({
        event: 'clic_tienda_externa',
        ecommerce: {
          currency: 'CLP',
          value: precioCLP,
          items: [{
            item_id: cafeId,
            item_name: cafeNombre,
            item_brand: tiendaNombre,
            item_category: 'Café de Especialidad',
            item_variant: `${formatoGramos}g`,
            price: precioCLP
          }]
        },
        // Parámetros de negocio en español
        tienda_destino: tiendaNombre,
        nombre_cafe: cafeNombre,
        formato_gramos: formatoGramos,
        precio_clp: precioCLP,
        precio_por_kilo: precioPorKilo,
        es_precio_estimado: Boolean(payload.esEstimado),
        url_salida: urlConUTM
      });

      if (typeof window.gtag === 'function') {
        window.gtag('event', 'clic_tienda_externa', {
          tienda_destino: tiendaNombre,
          nombre_cafe: cafeNombre,
          value: precioCLP,
          currency: 'CLP'
        });
      }
    }

    // Persistir métrica anónima en backend
    this.sendBeacon('clic_tienda_externa', {
      tienda_destino: tiendaNombre,
      nombre_cafe: cafeNombre,
      formato_gramos: formatoGramos,
      precio_clp: precioCLP,
      precio_por_kilo: precioPorKilo,
      es_precio_estimado: Boolean(payload.esEstimado),
      url_salida: urlConUTM,
      product_id: Number(cafeId) || undefined
    });

    return urlConUTM;
  }

  /**
   * Visualización de Directorio de Marcas (view_item_list).
   */
  static trackViewItemListMarcas(
    marcasVisibles: Array<{ id: number | string; nombre: string }>
  ): void {
    if (typeof window === 'undefined') return;
    window.dataLayer = window.dataLayer || [];
    window.dataLayer.push({ ecommerce: null });
    window.dataLayer.push({
      event: 'view_item_list',
      item_list_id: 'directorio_marcas',
      item_list_name: 'Directorio de Tostadurías',
      ecommerce: {
        items: marcasVisibles.map((marca, idx) => ({
          item_id: String(marca.id),
          item_name: marca.nombre,
          item_brand: marca.nombre,
          index: idx + 1
        }))
      }
    });
  }

  /**
   * Interacción con Marca en Directorio (seleccionar_marca).
   */
  static trackSeleccionarMarca(
    tiendaNombre: string,
    totalCafes: number,
    origenClic: string = 'tarjeta_directorio'
  ): void {
    if (typeof window === 'undefined') return;
    window.dataLayer = window.dataLayer || [];
    window.dataLayer.push({
      event: 'seleccionar_marca',
      tienda_nombre: tiendaNombre,
      total_cafes_activos: totalCafes,
      origen_clic: origenClic
    });

    this.sendBeacon('seleccionar_marca', {
      tienda_nombre: tiendaNombre,
      total_cafes_activos: totalCafes,
      origen_clic: origenClic
    });
  }

  /**
   * Comparativa Multitienda de Grano Idéntico (comparar_con_tienda).
   */
  static trackCompararConTienda(
    cafeId: number | string,
    tiendaActual: string,
    tiendaComparada: string,
    diffCLP: number,
    diffPorKilo: number
  ): void {
    if (typeof window === 'undefined') return;
    window.dataLayer = window.dataLayer || [];
    window.dataLayer.push({
      event: 'comparar_con_tienda',
      cafe_id: Number(cafeId),
      tienda_actual: tiendaActual,
      tienda_comparada: tiendaComparada,
      diferencia_precio_clp: diffCLP,
      diferencia_precio_kilo: diffPorKilo
    });

    this.sendBeacon('comparar_con_tienda', {
      cafe_id: Number(cafeId),
      tienda_actual: tiendaActual,
      tienda_comparada: tiendaComparada,
      diferencia_precio_clp: diffCLP,
      diferencia_precio_kilo: diffPorKilo
    });
  }

  // --- EVENTOS CANÓNICOS HEREDADOS (Compatibilidad hacia atrás) ---

  static trackSearch(searchTerm: string, sortBy: string = 'kilo', resultCount?: number): void {
    this.sendToDataLayer('search', {
      search_term: searchTerm,
      sort_by: sortBy,
      results_count: resultCount
    });
  }

  static trackSelectItem(productName: string, storeName: string, price: number, productId?: number): void {
    this.sendToDataLayer('select_item', {
      item_name: productName,
      item_brand: storeName,
      price: price,
      item_id: productId
    });
  }

  static trackViewItem(product: { id: number; nombre: string; tienda: string; precio: number }): void {
    this.sendToDataLayer('view_item', {
      item_id: product.id,
      item_name: product.nombre,
      item_brand: product.tienda,
      price: product.precio
    });
  }

  static trackOutboundClick(
    storeName: string,
    productName: string,
    price: number,
    destinationUrl: string,
    productId?: number | string,
    storeId?: number | string
  ): void {
    // Delegar al nuevo tracker enterprise para no perder parámetros de GA4
    this.trackClicTiendaExterna({
      cafeId: productId,
      cafeNombre: productName,
      tiendaNombre: storeName,
      productoPrecioCLP: price,
      destinationUrl: destinationUrl,
      productSlug: productName
    });

    this.sendToDataLayer('outbound_click', {
      store_name: storeName,
      store_id: storeId,
      tienda_id: storeId,
      product_name: productName,
      price: price,
      destination_url: destinationUrl,
      product_id: productId ? Number(productId) : undefined,
      item_id: productId ? Number(productId) : undefined,
    });
  }

  static trackAddToFavorites(productId: number | string, productName?: string, storeName?: string, price?: number, storeId?: number | string): void {
    this.sendToDataLayer('add_to_favorites', {
      product_id: Number(productId),
      item_id: Number(productId),
      product_name: productName,
      item_name: productName,
      store_name: storeName,
      store_id: storeId,
      tienda_id: storeId,
      price: price
    });
  }

  static trackAddToCompare(productId: number | string, productName?: string, storeName?: string, storeId?: number | string): void {
    this.sendToDataLayer('add_to_compare', {
      product_id: Number(productId),
      item_id: Number(productId),
      product_name: productName,
      store_name: storeName,
      store_id: storeId,
      tienda_id: storeId
    });
  }

  static trackRemoveFromCompare(productId: number): void {
    this.sendToDataLayer('remove_from_compare', {
      product_id: productId
    });
  }

  static trackCompareViewed(productCount: number, productIds: number[]): void {
    this.sendToDataLayer('compare_viewed', {
      compared_count: productCount,
      product_ids: productIds.join(',')
    });
  }

  static trackQuizCompleted(method: string, profile: string, acidity: string, topMatchId?: number): void {
    this.sendToDataLayer('quiz_completed', {
      brew_method: method,
      sensory_profile: profile,
      acidity: acidity,
      top_match_id: topMatchId
    });
  }

  static trackRecipeSaved(method: string, coffeeName: string, rating: number): void {
    this.sendToDataLayer('recipe_saved', {
      brew_method: method,
      coffee_name: coffeeName,
      rating: rating
    });
  }

  static trackRecipeCloudSynced(recipeCount: number): void {
    this.sendToDataLayer('recipe_cloud_synced', {
      recipes_synced: recipeCount
    });
  }

  static trackFeedbackSubmitted(category: string): void {
    this.sendToDataLayer('feedback_submitted', {
      category: category
    });
  }

  // --- EVENTOS TELEMETRÍA CARRITO WHATSAPP (SECCIÓN 5) ---

  static trackAddToCart(item: { itemName: string; price: number; storeName: string; productId?: number | string }): void {
    this.sendToDataLayer('add_to_cart', {
      item_name: item.itemName,
      price: item.price,
      store_name: item.storeName,
      item_id: item.productId,
    });
  }

  static trackRemoveFromCart(item: { itemName: string; storeName: string; productId?: number | string }): void {
    this.sendToDataLayer('remove_from_cart', {
      item_name: item.itemName,
      store_name: item.storeName,
      item_id: item.productId,
    });
  }

  static trackViewCart(itemsCount: number, storesCount: number): void {
    this.sendToDataLayer('view_cart', {
      items_count: itemsCount,
      stores_count: storesCount,
    });
  }

  static trackGenerateWhatsAppOrder(payload: { totalClp: number; itemsCount: number; storeId: number | string; storeName: string }): void {
    this.sendToDataLayer('generate_whatsapp_order', {
      total_clp: payload.totalClp,
      items_count: payload.itemsCount,
      store_id: payload.storeId,
      store_name: payload.storeName,
    });
  }
}
