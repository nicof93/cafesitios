import { describe, it, expect } from 'vitest';
import { ProductVariant } from '../../src/core/domain/models/ProductVariant';

describe('ProductVariant Entity (RN-02 & Precios)', () => {
  it('calcula correctamente el precio por kilo oficial', () => {
    const variant = new ProductVariant({
      id: 1,
      opcion: 'Grano',
      precio_clp: 10000,
      precio_original_clp: 10000,
      precio_por_kilo: 0,
      formato_gramos: 250,
      disponible: true,
      en_oferta: false,
      descuento_porcentaje: 0,
      es_estimado: false
    });

    expect(variant.precio_por_kilo).toBe(40000);
    expect(variant.es_estimado).toBe(false);
  });

  it('aplica flag es_estimado cuando el gramaje fue por fallback (RN-02)', () => {
    const variant = new ProductVariant({
      id: 2,
      opcion: 'Estándar',
      precio_clp: 8000,
      precio_original_clp: 8000,
      precio_por_kilo: 0,
      formato_gramos: 250,
      disponible: true,
      en_oferta: false,
      descuento_porcentaje: 0,
      es_estimado: true
    });

    expect(variant.es_estimado).toBe(true);
    expect(variant.precio_por_kilo).toBe(32000);
  });

  it('calcula porcentaje de descuento cuando está en oferta', () => {
    const variant = new ProductVariant({
      id: 3,
      opcion: 'Molido',
      precio_clp: 15000,
      precio_original_clp: 20000,
      precio_por_kilo: 0,
      formato_gramos: 500,
      disponible: true,
      en_oferta: true,
      descuento_porcentaje: 0,
      es_estimado: false
    });

    expect(variant.en_oferta).toBe(true);
    expect(variant.descuento_porcentaje).toBe(25);
  });

  it('identifica muestras gratuitas ($0 CLP)', () => {
    const variant = new ProductVariant({
      id: 4,
      opcion: 'Muestra',
      precio_clp: 0,
      precio_original_clp: 0,
      precio_por_kilo: 0,
      formato_gramos: 50,
      disponible: true,
      en_oferta: false,
      descuento_porcentaje: 0,
      es_estimado: false
    });

    expect(variant.isFree()).toBe(true);
    expect(variant.precio_por_kilo).toBe(0);
  });
});

