export interface ChartPricePoint {
  label: string;
  value: number;
  rawDate?: string;
}

export interface RawPriceHistoryItem {
  id?: number;
  precio_clp: number;
  precio_original_clp?: number;
  precio_por_kilo: number;
  fecha_registro?: string;
}

/**
 * Filtra los puntos de historial de precios para una representación gráfica óptima y limpia.
 * Regla de negocio:
 * 1. Si no hay registros, genera una línea base de 2 puntos representativos ('Hace 30d' y 'Hoy').
 * 2. Si no han habido cambios en la serie histórica (todos los valores son iguales), toma únicamente
 *    el primer valor registrado y el último para mostrar.
 * 3. Si han habido cambios, muestra la fecha y valores donde ha habido variaciones:
 *    el valor inicial, cada punto donde el precio cambia con respecto al anterior,
 *    y el último valor registrado para reflejar la vigencia actual.
 */
export function filterSignificantPriceHistory(
  historial: RawPriceHistoryItem[] | undefined | null,
  isKilo: boolean,
  currentVal: number
): ChartPricePoint[] {
  if (!historial || historial.length === 0) {
    return [
      { label: 'Hace 30d', value: currentVal },
      { label: 'Hoy', value: currentVal }
    ];
  }

  // Ordenar cronológicamente ascendente
  const sorted = [...historial].sort((a, b) => {
    const tA = a.fecha_registro ? new Date(a.fecha_registro).getTime() : 0;
    const tB = b.fecha_registro ? new Date(b.fecha_registro).getTime() : 0;
    return tA - tB;
  });

  const allMapped: ChartPricePoint[] = sorted.map((h, idx) => {
    const val = Math.round(isKilo ? (h.precio_por_kilo || currentVal) : (h.precio_clp || currentVal));
    const label = h.fecha_registro
      ? new Date(h.fecha_registro).toLocaleDateString('es-CL', { day: '2-digit', month: 'short' })
      : `P${idx + 1}`;
    return { label, value: val, rawDate: h.fecha_registro };
  });

  // Si solo hay un punto registrado en toda la historia
  if (allMapped.length === 1) {
    return [
      allMapped[0],
      { label: 'Hoy', value: allMapped[0].value, rawDate: new Date().toISOString() }
    ];
  }

  // Verificar si hay cambios en los valores registrados
  const firstVal = allMapped[0].value;
  const hasChanges = allMapped.some(p => p.value !== firstVal);

  if (!hasChanges) {
    // Si no han habido cambios, toma el primer valor registrado y el último
    return [
      allMapped[0],
      allMapped[allMapped.length - 1]
    ];
  }

  // Solo mostrar la fecha y valores que han cambiado
  const result: ChartPricePoint[] = [];

  // 1. Primer valor registrado (origen de la serie)
  result.push(allMapped[0]);

  // 2. Puntos donde el valor cambia respecto al valor anterior
  for (let i = 1; i < allMapped.length; i++) {
    if (allMapped[i].value !== allMapped[i - 1].value) {
      result.push(allMapped[i]);
    }
  }

  // 3. Incluir el último valor registrado si no coincide con el último agregado
  const lastPoint = allMapped[allMapped.length - 1];
  const lastResult = result[result.length - 1];
  if (lastPoint !== lastResult && (lastPoint.rawDate !== lastResult.rawDate || lastPoint.value !== lastResult.value)) {
    result.push(lastPoint);
  }

  return result;
}

