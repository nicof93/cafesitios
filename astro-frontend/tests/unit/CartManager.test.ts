import { describe, it, expect, beforeEach } from 'vitest';
import { CartManager, CART_STORAGE_KEY } from '../../src/core/application/CartManager';

describe('CartManager', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('inicia vacío si no hay datos en localStorage', () => {
    expect(CartManager.getItems()).toEqual([]);
    expect(CartManager.getTotalCount()).toBe(0);
  });

  it('agrega un producto correctamente y calcula totalCount', () => {
    CartManager.addItem({
      productId: 10,
      nombre: 'Etiopía Guji',
      formatoGramos: 250,
      molienda: 'V60',
      cantidad: 2,
      precioUnitarioClp: 11000,
      tiendaId: 1,
      tiendaNombre: 'Tostaduría Central',
      tiendaWhatsapp: '+56912345678',
    });

    const items = CartManager.getItems();
    expect(items.length).toBe(1);
    expect(items[0].nombre).toBe('Etiopía Guji');
    expect(items[0].cantidad).toBe(2);
    expect(CartManager.getTotalCount()).toBe(2);
  });

  it('incrementa cantidad si se agrega el mismo producto y formato', () => {
    CartManager.addItem({
      productId: 10,
      nombre: 'Etiopía Guji',
      formatoGramos: 250,
      molienda: 'V60',
      cantidad: 1,
      precioUnitarioClp: 11000,
      tiendaId: 1,
      tiendaNombre: 'Tostaduría Central',
    });

    CartManager.addItem({
      productId: 10,
      nombre: 'Etiopía Guji',
      formatoGramos: 250,
      molienda: 'V60',
      cantidad: 2,
      precioUnitarioClp: 11000,
      tiendaId: 1,
      tiendaNombre: 'Tostaduría Central',
    });

    const items = CartManager.getItems();
    expect(items.length).toBe(1);
    expect(items[0].cantidad).toBe(3);
    expect(CartManager.getTotalCount()).toBe(3);
  });

  it('agrupa por tienda y calcula subtotales y precio promedio por kilo', () => {
    CartManager.addItem({
      productId: 10,
      nombre: 'Etiopía Guji',
      formatoGramos: 250,
      molienda: 'V60',
      cantidad: 2, // 500g, $22.000
      precioUnitarioClp: 11000,
      tiendaId: 1,
      tiendaNombre: 'Tostaduría Central',
      tiendaWhatsapp: '+56912345678',
    });

    CartManager.addItem({
      productId: 11,
      nombre: 'Colombia Supremo',
      formatoGramos: 500,
      molienda: 'Grano',
      cantidad: 1, // 500g, $14.500
      precioUnitarioClp: 14500,
      tiendaId: 1,
      tiendaNombre: 'Tostaduría Central',
      tiendaWhatsapp: '+56912345678',
    });

    CartManager.addItem({
      productId: 20,
      nombre: 'Brasil Cerrado',
      formatoGramos: 250,
      molienda: 'Espresso',
      cantidad: 1, // 250g, $9.000
      precioUnitarioClp: 9000,
      tiendaId: 2,
      tiendaNombre: 'Tostaduría Sur',
      tiendaWhatsapp: '+56999999999',
    });

    const groups = CartManager.getGroupedByStore();
    expect(groups.length).toBe(2);

    const group1 = groups.find(g => String(g.tiendaId) === '1');
    expect(group1).toBeDefined();
    expect(group1!.subtotalClp).toBe(36500); // 22000 + 14500
    expect(group1!.totalGramos).toBe(1000); // 250*2 + 500
    expect(group1!.precioPromedioKiloClp).toBe(36500);

    const group2 = groups.find(g => String(g.tiendaId) === '2');
    expect(group2!.subtotalClp).toBe(9000);
    expect(group2!.totalGramos).toBe(250);
    expect(group2!.precioPromedioKiloClp).toBe(36000);
  });

  it('genera el formato de mensaje de WhatsApp con Markdown requerido', () => {
    CartManager.addItem({
      productId: 10,
      nombre: 'Etiopía Guji',
      formatoGramos: 250,
      molienda: 'V60',
      cantidad: 2,
      precioUnitarioClp: 11000,
      tiendaId: 1,
      tiendaNombre: 'Tostaduría Central',
      tiendaWhatsapp: '+56912345678',
    });

    const groups = CartManager.getGroupedByStore();
    const message = CartManager.buildWhatsAppMessage(groups[0]);

    expect(message).toContain('¡Hola *Tostaduría Central*! 👋');
    expect(message).toContain('Vi tus productos en *Cafesitios*');
    expect(message).toContain('• *2x* Etiopía Guji (250g, V60) - $22.000 CLP');
    expect(message).toContain('💰 *TOTAL ESTIMADO:* $22.000 CLP');
    expect(message).toContain('📍 *DESPACHO / RETIRO:*');
    expect(message).toContain('👤 *NOMBRE CLIENTE:*');
  });

  it('permite incrementar, decrementar y eliminar ítems', () => {
    CartManager.addItem({
      productId: 10,
      nombre: 'Etiopía Guji',
      formatoGramos: 250,
      molienda: 'V60',
      cantidad: 1,
      precioUnitarioClp: 11000,
      tiendaId: 1,
      tiendaNombre: 'Tostaduría Central',
    });

    const itemId = CartManager.getItems()[0].id;
    CartManager.increment(itemId);
    expect(CartManager.getItems()[0].cantidad).toBe(2);

    CartManager.decrement(itemId);
    expect(CartManager.getItems()[0].cantidad).toBe(1);

    CartManager.decrement(itemId); // llega a 0 -> se elimina
    expect(CartManager.getItems().length).toBe(0);
  });
});
