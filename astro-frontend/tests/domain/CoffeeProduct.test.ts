import { describe, it, expect } from 'vitest';
import { CoffeeProduct } from '../../src/core/domain/models/CoffeeProduct';

describe('CoffeeProduct Entity', () => {
  it('selecciona la variante disponible más económica por kilo', () => {
    const product = new CoffeeProduct({
      id: 10,
      nombre: 'Geisha Hacienda La Esmeralda',
      tienda: 'Singular',
      url_detalle: 'https://singular.cl/geisha',
      variantes: [
        {
          id: 101,
          opcion: '250g',
          precio_clp: 18000,
          precio_original_clp: 18000,
          precio_por_kilo: 72000,
          formato_gramos: 250,
          disponible: true,
          en_oferta: false,
          descuento_porcentaje: 0,
          es_estimado: false
        },
        {
          id: 102,
          opcion: '1kg',
          precio_clp: 50000,
          precio_original_clp: 50000,
          precio_por_kilo: 50000,
          formato_gramos: 1000,
          disponible: true,
          en_oferta: false,
          descuento_porcentaje: 0,
          es_estimado: false
        }
      ]
    });

    const best = product.getBestVariant(true);
    expect(best).toBeDefined();
    expect(best?.formato_gramos).toBe(1000);
    expect(best?.precio_por_kilo).toBe(50000);
  });

  it('ignora variantes agotadas si se requiere disponible', () => {
    const product = new CoffeeProduct({
      id: 11,
      nombre: 'Bourbon Rosado',
      tienda: 'We Are Four',
      url_detalle: 'https://wearefour.cl/bourbon',
      variantes: [
        {
          id: 111,
          opcion: '1kg (Agotado)',
          precio_clp: 30000,
          precio_original_clp: 30000,
          precio_por_kilo: 30000,
          formato_gramos: 1000,
          disponible: false,
          en_oferta: false,
          descuento_porcentaje: 0,
          es_estimado: false
        },
        {
          id: 112,
          opcion: '250g',
          precio_clp: 12000,
          precio_original_clp: 12000,
          precio_por_kilo: 48000,
          formato_gramos: 250,
          disponible: true,
          en_oferta: false,
          descuento_porcentaje: 0,
          es_estimado: false
        }
      ]
    });

    const bestAvailable = product.getBestVariant(true);
    expect(bestAvailable?.id).toBe(112);
  });

  it('normaliza notas_cata tanto desde objetos como desde strings simples', () => {
    const product = new CoffeeProduct({
      id: 20,
      nombre: 'Geisha Floral',
      tienda: 'Tostador Test',
      url_detalle: 'https://test.cl',
      notas_cata: [
        { nombre: 'Jazmín', clave_normalizada: 'jazmin' },
        { clave_normalizada: 'frutos-rojos' },
        'Caramelo'
      ]
    });

    expect(product.notas_cata).toEqual(['Jazmín', 'frutos-rojos', 'Caramelo']);
  });

  it('sintetiza una variante válida cuando recibe precios directos (como en sustitutos/matches)', () => {
    const product = new CoffeeProduct({
      id: 30,
      nombre: 'Colombia Huila Sustituto',
      tienda: 'Otra Tienda',
      url_detalle: 'https://otratienda.cl/huila',
      precio_clp: 11990,
      precio_por_kilo: 47960,
      formato_gramos: 250,
    });

    const best = product.getBestVariant(true);
    expect(best).toBeDefined();
    expect(best?.precio_clp).toBe(11990);
    expect(best?.precio_por_kilo).toBe(47960);
    expect(best?.formato_gramos).toBe(250);
  });

  it('normaliza notas_confirmadas y notas_sugeridas correctamente', () => {
    const product = new CoffeeProduct({
      id: 40,
      nombre: 'Kenia Nyeri AA',
      tienda: 'Tostaduría Austral',
      url_detalle: 'https://austral.cl/kenia',
      notas_confirmadas: ['Grosella negra', { nombre: 'Pomelo rosado' }],
      notas_sugeridas: ['Vino tinto', { nombre: 'Mora silvestre' }],
    });

    expect(product.notas_confirmadas).toEqual(['Grosella negra', 'Pomelo rosado']);
    expect(product.notas_sugeridas).toEqual(['Vino tinto', 'Mora silvestre']);
  });

  it('evita que las notas sugeridas dupliquen descriptores ya confirmados', () => {
    const product = new CoffeeProduct({
      id: 50,
      nombre: 'Perú Cajamarca Dark',
      tienda: 'Tostaduría Andina',
      url_detalle: 'https://andina.cl/cajamarca',
      notas_confirmadas: ['Fruta', 'Frutas Rojas'],
      notas_sugeridas: ['fruta', 'Frutas rojas', 'Chancaca'],
    });

    expect(product.notas_confirmadas).toEqual(['Fruta', 'Frutas Rojas']);
    // 'fruta' y 'Frutas rojas' deben ser eliminadas de sugeridas
    expect(product.notas_sugeridas).toEqual(['Chancaca']);
  });
});

