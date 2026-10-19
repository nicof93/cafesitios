import { AnalyticsTracker } from '../infrastructure/analytics/AnalyticsTracker';

export interface CartItem {
  id: string; // formato: `${productId}_${formatoGramos}_${molienda}`
  productId: number | string;
  nombre: string;
  formatoGramos: number;
  molienda: string;
  cantidad: number;
  precioUnitarioClp: number;
  tiendaId: number | string;
  tiendaNombre: string;
  tiendaWhatsapp?: string;
  imagen?: string;
  urlDetalle?: string;
}

export interface StoreCartGroup {
  tiendaId: number | string;
  tiendaNombre: string;
  tiendaWhatsapp?: string;
  items: CartItem[];
  subtotalClp: number;
  totalGramos: number;
  precioPromedioKiloClp: number;
}

export const CART_STORAGE_KEY = 'cafesitios_cart_v1';
export const DEVICE_UUID_STORAGE_KEY = 'cafesitios_device_uuid_v1';

export class CartManager {
  private static listeners: Array<(items: CartItem[]) => void> = [];

  /**
   * Obtiene o genera un identificador anónimo de dispositivo para trazabilidad de leads.
   */
  static getOrCreateDeviceUuid(): string {
    if (typeof window === 'undefined') return 'server-rendered-device-uuid';
    try {
      let uuid = localStorage.getItem(DEVICE_UUID_STORAGE_KEY);
      if (!uuid) {
        uuid = (typeof crypto !== 'undefined' && crypto.randomUUID)
          ? crypto.randomUUID()
          : `cs-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;
        localStorage.setItem(DEVICE_UUID_STORAGE_KEY, uuid);
      }
      return uuid;
    } catch {
      return 'fallback-device-uuid';
    }
  }

  static getItems(): CartItem[] {
    if (typeof window === 'undefined') return [];
    try {
      const raw = localStorage.getItem(CART_STORAGE_KEY);
      if (!raw) return [];
      const parsed = JSON.parse(raw);
      return Array.isArray(parsed) ? parsed : [];
    } catch {
      return [];
    }
  }

  private static saveItems(items: CartItem[]): void {
    if (typeof window === 'undefined') return;
    try {
      localStorage.setItem(CART_STORAGE_KEY, JSON.stringify(items));
    } catch (e) {
      console.error('Error guardando en localStorage el carrito:', e);
    }
    this.notify(items);
  }

  static subscribe(listener: (items: CartItem[]) => void): () => void {
    this.listeners.push(listener);
    return () => {
      this.listeners = this.listeners.filter(l => l !== listener);
    };
  }

  private static notify(items: CartItem[]): void {
    for (const listener of this.listeners) {
      try {
        listener(items);
      } catch (err) {
        console.error('Error in cart subscriber:', err);
      }
    }
    // Disparar evento personalizado en window para interoperabilidad en componentes Astro
    if (typeof window !== 'undefined') {
      window.dispatchEvent(new CustomEvent('cafesitios:cart-updated', { detail: { items } }));
    }
  }

  /**
   * Agrega un ítem al carrito o incrementa su cantidad.
   */
  static addItem(item: Omit<CartItem, 'id'>): void {
    const items = this.getItems();
    const itemId = `${item.productId}_${item.formatoGramos}_${(item.molienda || 'Grano').trim()}`;
    const existingIndex = items.findIndex(i => i.id === itemId);

    if (existingIndex >= 0) {
      items[existingIndex].cantidad += item.cantidad || 1;
    } else {
      items.push({
        ...item,
        id: itemId,
        cantidad: item.cantidad || 1,
      });
    }

    this.saveItems(items);

    // Telemetría GA4/GTM
    AnalyticsTracker.trackAddToCart({
      itemName: item.nombre,
      price: item.precioUnitarioClp,
      storeName: item.tiendaNombre,
      productId: item.productId,
    });
  }

  /**
   * Incrementa en 1 la cantidad.
   */
  static increment(itemId: string): void {
    const items = this.getItems();
    const target = items.find(i => i.id === itemId);
    if (target) {
      target.cantidad += 1;
      this.saveItems(items);
    }
  }

  /**
   * Decrementa en 1 o elimina si llega a 0.
   */
  static decrement(itemId: string): void {
    let items = this.getItems();
    const target = items.find(i => i.id === itemId);
    if (target) {
      if (target.cantidad > 1) {
        target.cantidad -= 1;
      } else {
        items = items.filter(i => i.id !== itemId);
        AnalyticsTracker.trackRemoveFromCart({
          itemName: target.nombre,
          storeName: target.tiendaNombre,
          productId: target.productId,
        });
      }
      this.saveItems(items);
    }
  }

  /**
   * Elimina un ítem específico.
   */
  static removeItem(itemId: string): void {
    let items = this.getItems();
    const target = items.find(i => i.id === itemId);
    if (target) {
      items = items.filter(i => i.id !== itemId);
      this.saveItems(items);
      AnalyticsTracker.trackRemoveFromCart({
        itemName: target.nombre,
        storeName: target.tiendaNombre,
        productId: target.productId,
      });
    }
  }

  /**
   * Vacía los ítems de una tostaduría específica.
   */
  static clearStore(tiendaId: number | string): void {
    const items = this.getItems().filter(i => String(i.tiendaId) !== String(tiendaId));
    this.saveItems(items);
  }

  /**
   * Vacía la totalidad del carrito.
   */
  static clearAll(): void {
    this.saveItems([]);
  }

  /**
   * Cantidad total de paquetes en el carrito.
   */
  static getTotalCount(): number {
    return this.getItems().reduce((acc, curr) => acc + curr.cantidad, 0);
  }

  /**
   * Agrupa los ítems por tostaduría con cálculo de subtotales y precio estimado por kilo.
   */
  static getGroupedByStore(): StoreCartGroup[] {
    const items = this.getItems();
    const groupsMap = new Map<string, StoreCartGroup>();

    for (const item of items) {
      const key = String(item.tiendaId || item.tiendaNombre);
      let group = groupsMap.get(key);
      if (!group) {
        group = {
          tiendaId: item.tiendaId,
          tiendaNombre: item.tiendaNombre,
          tiendaWhatsapp: item.tiendaWhatsapp,
          items: [],
          subtotalClp: 0,
          totalGramos: 0,
          precioPromedioKiloClp: 0,
        };
        groupsMap.set(key, group);
      }
      group.items.push(item);
      group.subtotalClp += item.precioUnitarioClp * item.cantidad;
      group.totalGramos += (item.formatoGramos || 250) * item.cantidad;
      if (!group.tiendaWhatsapp && item.tiendaWhatsapp) {
        group.tiendaWhatsapp = item.tiendaWhatsapp;
      }
    }

    const result = Array.from(groupsMap.values());
    for (const g of result) {
      if (g.totalGramos > 0) {
        g.precioPromedioKiloClp = Math.round((g.subtotalClp / g.totalGramos) * 1000);
      }
    }

    return result;
  }

  /**
   * Genera el texto Markdown enriquecido para WhatsApp de una tostaduría.
   */
  static buildWhatsAppMessage(group: StoreCartGroup): string {
    const lines: string[] = [
      `¡Hola *${group.tiendaNombre}*! 👋`,
      `Vi tus productos en *Cafesitios* y me gustaría realizar el siguiente pedido:`,
      '',
      `🛒 *DETALLE DEL PEDIDO:*`
    ];

    for (const item of group.items) {
      const totalItem = (item.precioUnitarioClp * item.cantidad).toLocaleString('es-CL');
      const moliendaText = item.molienda ? `, ${item.molienda}` : '';
      lines.push(`• *${item.cantidad}x* ${item.nombre} (${item.formatoGramos}g${moliendaText}) - $${totalItem} CLP`);
    }

    lines.push('');
    lines.push(`💰 *TOTAL ESTIMADO:* $${group.subtotalClp.toLocaleString('es-CL')} CLP`);
    lines.push('');
    lines.push(`📍 *DESPACHO / RETIRO:* [Escribe tu comuna o si prefieres retiro]`);
    lines.push(`👤 *NOMBRE CLIENTE:* [Tu nombre]`);
    lines.push('');
    lines.push(`¿Me confirman disponibilidad para coordinar el pago por transferencia? ¡Muchas gracias!`);

    return lines.join('\n');
  }

  /**
   * Genera la URL de WhatsApp (wa.me) con mensaje codificado.
   */
  static getWhatsAppUrl(group: StoreCartGroup): string {
    const phone = (group.tiendaWhatsapp || '').replace(/[^0-9]/g, '');
    const message = this.buildWhatsAppMessage(group);
    const encoded = encodeURIComponent(message);
    return `https://wa.me/${phone}?text=${encoded}`;
  }

  /**
   * Envía lead asíncrono a la API y abre el enlace de WhatsApp.
   */
  static async checkoutStoreViaWhatsApp(group: StoreCartGroup, apiBaseUrl: string = ''): Promise<void> {
    const deviceUuid = this.getOrCreateDeviceUuid();

    // Telemetría GA4/GTM
    AnalyticsTracker.trackGenerateWhatsAppOrder({
      totalClp: group.subtotalClp,
      itemsCount: group.items.reduce((acc, i) => acc + i.cantidad, 0),
      storeId: group.tiendaId,
      storeName: group.tiendaNombre,
    });

    const leadPayload = {
      tienda_id: group.tiendaId,
      dispositivo_uuid: deviceUuid,
      monto_total_clp: group.subtotalClp,
      items: group.items.map(i => ({
        producto_id: String(i.productId),
        nombre: i.nombre,
        formato: `${i.formatoGramos}g`,
        molienda: i.molienda || 'Grano entero',
        cantidad: i.cantidad,
        precio_unitario_clp: i.precioUnitarioClp,
      })),
    };

    // Envío asíncrono no bloqueante
    try {
      const endpoint = `${apiBaseUrl.replace(/\/$/, '')}/api/v1/orders/whatsapp-lead`;
      fetch(endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(leadPayload),
      }).catch(err => {
        console.warn('No se pudo registrar lead previo en servidor:', err);
      });
    } catch {
      // Ignorar fallas de red para no interrumpir la compra del usuario
    }

    // Abrir WhatsApp en nueva pestaña
    const waUrl = this.getWhatsAppUrl(group);
    window.open(waUrl, '_blank', 'noopener,noreferrer');
  }
}
