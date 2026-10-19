import { Environment } from '../config/Environment';

declare global {
  interface Window {
    dataLayer?: unknown[];
    gtag?: (...args: unknown[]) => void;
  }
}

export class AnalyticsTracker {
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
    if (typeof window === 'undefined' || !navigator.sendBeacon) return;
    if (typeof process !== 'undefined' && (process.env.NODE_ENV === 'test' || process.env.VITEST)) return;

    try {
      const url = `${Environment.getApiBaseUrl()}/api/v1/telemetry/event`;
      const payload = JSON.stringify({
        event_type: eventType,
        metadata
      });
      navigator.sendBeacon(url, new Blob([payload], { type: 'application/json' }));
    } catch {
      // Ignorar errores en segundo plano
    }
  }

  // --- 11 EVENTOS CANÓNICOS (SRS v2.0 Sección 7) ---

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

  static trackOutboundClick(storeName: string, productName: string, price: number, destinationUrl: string): void {
    this.sendToDataLayer('outbound_click', {
      store_name: storeName,
      product_name: productName,
      price: price,
      destination_url: destinationUrl
    });
  }

  static trackAddToCompare(productId: number, productName?: string): void {
    this.sendToDataLayer('add_to_compare', {
      product_id: productId,
      product_name: productName
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

