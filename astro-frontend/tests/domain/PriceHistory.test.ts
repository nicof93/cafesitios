import { describe, it, expect } from 'vitest';
import { filterSignificantPriceHistory, type RawPriceHistoryItem } from '../../src/core/domain/priceHistory';

describe('filterSignificantPriceHistory', () => {
  it('genera dos puntos por defecto cuando no hay historial registrado', () => {
    const points = filterSignificantPriceHistory([], false, 12990);
    expect(points).toHaveLength(2);
    expect(points[0].label).toBe('Hace 30d');
    expect(points[0].value).toBe(12990);
    expect(points[1].label).toBe('Hoy');
    expect(points[1].value).toBe(12990);
  });

  it('cuando solo existe 1 registro histórico, muestra ese registro y el punto actual', () => {
    const history: RawPriceHistoryItem[] = [
      { precio_clp: 14500, precio_por_kilo: 58000, fecha_registro: '2026-10-01T10:00:00Z' }
    ];
    const points = filterSignificantPriceHistory(history, false, 14500);
    expect(points).toHaveLength(2);
    expect(points[0].value).toBe(14500);
    expect(points[1].label).toBe('Hoy');
  });

  it('cuando no han habido cambios en múltiples registros, toma solo el primer valor registrado y el último', () => {
    const history: RawPriceHistoryItem[] = [
      { precio_clp: 11990, precio_por_kilo: 47960, fecha_registro: '2026-10-01T08:00:00Z' },
      { precio_clp: 11990, precio_por_kilo: 47960, fecha_registro: '2026-10-02T08:00:00Z' },
      { precio_clp: 11990, precio_por_kilo: 47960, fecha_registro: '2026-10-05T08:00:00Z' },
      { precio_clp: 11990, precio_por_kilo: 47960, fecha_registro: '2026-10-10T08:00:00Z' },
      { precio_clp: 11990, precio_por_kilo: 47960, fecha_registro: '2026-10-15T08:00:00Z' },
      { precio_clp: 11990, precio_por_kilo: 47960, fecha_registro: '2026-10-20T08:00:00Z' },
      { precio_clp: 11990, precio_por_kilo: 47960, fecha_registro: '2026-10-24T08:00:00Z' },
    ];

    const points = filterSignificantPriceHistory(history, false, 11990);
    expect(points).toHaveLength(2);
    expect(points[0].rawDate).toBe('2026-10-01T08:00:00Z');
    expect(points[0].value).toBe(11990);
    expect(points[1].rawDate).toBe('2026-10-24T08:00:00Z');
    expect(points[1].value).toBe(11990);
  });

  it('cuando han habido cambios, solo muestra las fechas y valores que han variado y extremos vigentes', () => {
    const history: RawPriceHistoryItem[] = [
      { precio_clp: 10000, precio_por_kilo: 40000, fecha_registro: '2026-10-01T00:00:00Z' }, // 1. Inicial
      { precio_clp: 10000, precio_por_kilo: 40000, fecha_registro: '2026-10-03T00:00:00Z' },
      { precio_clp: 12000, precio_por_kilo: 48000, fecha_registro: '2026-10-08T00:00:00Z' }, // 2. Subió
      { precio_clp: 12000, precio_por_kilo: 48000, fecha_registro: '2026-10-12T00:00:00Z' },
      { precio_clp: 11500, precio_por_kilo: 46000, fecha_registro: '2026-10-16T00:00:00Z' }, // 3. Bajó
      { precio_clp: 11500, precio_por_kilo: 46000, fecha_registro: '2026-10-20T00:00:00Z' },
      { precio_clp: 11500, precio_por_kilo: 46000, fecha_registro: '2026-10-24T00:00:00Z' }, // 4. Último vigente
    ];

    const points = filterSignificantPriceHistory(history, false, 11500);
    expect(points).toHaveLength(4);
    expect(points.map(p => p.value)).toEqual([10000, 12000, 11500, 11500]);
    expect(points[0].rawDate).toBe('2026-10-01T00:00:00Z');
    expect(points[1].rawDate).toBe('2026-10-08T00:00:00Z');
    expect(points[2].rawDate).toBe('2026-10-16T00:00:00Z');
    expect(points[3].rawDate).toBe('2026-10-24T00:00:00Z');
  });

  it('funciona correctamente en modo precio por kilo ($/kg)', () => {
    const history: RawPriceHistoryItem[] = [
      { precio_clp: 10000, precio_por_kilo: 40000, fecha_registro: '2026-10-01T00:00:00Z' },
      { precio_clp: 10000, precio_por_kilo: 40000, fecha_registro: '2026-10-05T00:00:00Z' },
      { precio_clp: 12500, precio_por_kilo: 50000, fecha_registro: '2026-10-10T00:00:00Z' },
    ];

    const pointsKilo = filterSignificantPriceHistory(history, true, 50000);
    expect(pointsKilo).toHaveLength(2);
    expect(pointsKilo[0].value).toBe(40000);
    expect(pointsKilo[1].value).toBe(50000);
  });
});

