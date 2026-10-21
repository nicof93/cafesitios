export interface FavoriteItem {
  cafe_id: number;
  nombre: string;
  tienda: string;
  imagen?: string;
  url_detalle?: string;
  ultimo_precio_guardado: number;
  ultimo_precio_kilo_guardado?: number;
  ultimo_stock_disponible: boolean;
  fecha_guardado: string;
  // Campos dinámicos de variación
  precio_actual?: number;
  precio_kilo_actual?: number;
  disponible_actual?: boolean;
  diferencia_precio?: number;
  porcentaje_variacion?: number;
  tipo_variacion?: 'BAJO' | 'SUBIO' | 'IGUAL';
  volvio_disponible?: boolean;
}

const STORAGE_KEY = 'cafesitios_favoritos_v1';

export class FavoritesAdapter {
  static getFavorites(): FavoriteItem[] {
    if (typeof window === 'undefined') return [];
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) return [];
      const parsed = JSON.parse(raw);
      return Array.isArray(parsed) ? parsed : [];
    } catch (e) {
      console.warn('Error leyendo favoritos de localStorage:', e);
      return [];
    }
  }

  static isFavorite(cafeId: number | string): boolean {
    const idNum = Number(cafeId);
    return this.getFavorites().some((f) => f.cafe_id === idNum);
  }

  static toggleFavorite(data: {
    cafe_id: number | string;
    nombre: string;
    tienda: string;
    imagen?: string;
    url_detalle?: string;
    ultimo_precio_guardado: number;
    ultimo_precio_kilo_guardado?: number;
    ultimo_stock_disponible?: boolean;
  }): boolean {
    if (typeof window === 'undefined') return false;
    const idNum = Number(data.cafe_id);
    const existing = this.getFavorites();
    const index = existing.findIndex((f) => f.cafe_id === idNum);

    let isAdded = false;
    if (index >= 0) {
      existing.splice(index, 1);
      isAdded = false;
    } else {
      existing.unshift({
        cafe_id: idNum,
        nombre: data.nombre,
        tienda: data.tienda,
        imagen: data.imagen,
        url_detalle: data.url_detalle,
        ultimo_precio_guardado: Number(data.ultimo_precio_guardado) || 0,
        ultimo_precio_kilo_guardado: data.ultimo_precio_kilo_guardado ? Number(data.ultimo_precio_kilo_guardado) : undefined,
        ultimo_stock_disponible: data.ultimo_stock_disponible !== false,
        fecha_guardado: new Date().toISOString(),
      });
      isAdded = true;
    }

    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(existing));
      window.dispatchEvent(
        new CustomEvent('cafesitios:favorites-updated', {
          detail: { cafe_id: idNum, isAdded, favorites: existing },
        })
      );
    } catch (e) {
      console.warn('Error guardando favoritos en localStorage:', e);
    }
    return isAdded;
  }

  static removeFavorite(cafeId: number | string): void {
    if (typeof window === 'undefined') return;
    const idNum = Number(cafeId);
    const filtered = this.getFavorites().filter((f) => f.cafe_id !== idNum);
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(filtered));
      window.dispatchEvent(
        new CustomEvent('cafesitios:favorites-updated', {
          detail: { cafe_id: idNum, isAdded: false, favorites: filtered },
        })
      );
    } catch (e) {
      console.warn('Error actualizando favoritos en localStorage:', e);
    }
  }

  static evaluateVariations(
    currentCatalogProducts: Array<{
      id: number;
      nombre: string;
      tienda: string;
      imagen?: string;
      url_detalle?: string;
      variante?: { precio_clp: number; precio_por_kilo: number; disponible: boolean };
      precio_clp?: number;
      precio_por_kilo?: number;
      disponible?: boolean;
    }>
  ): FavoriteItem[] {
    const favorites = this.getFavorites();
    if (!favorites.length || !currentCatalogProducts?.length) return favorites;

    const catalogMap = new Map<number, any>();
    for (const p of currentCatalogProducts) {
      catalogMap.set(Number(p.id), p);
    }

    return favorites.map((fav) => {
      const match = catalogMap.get(fav.cafe_id);
      if (!match) return fav;

      const precioActual = Number(match.variante?.precio_clp ?? match.precio_clp ?? fav.ultimo_precio_guardado);
      const precioKiloActual = Number(match.variante?.precio_por_kilo ?? match.precio_por_kilo ?? fav.ultimo_precio_kilo_guardado ?? 0);
      const disponibleActual = match.variante?.disponible ?? match.disponible ?? fav.ultimo_stock_disponible;

      const diff = precioActual - fav.ultimo_precio_guardado;
      let tipo: 'BAJO' | 'SUBIO' | 'IGUAL' = 'IGUAL';
      let pct = 0;

      if (fav.ultimo_precio_guardado > 0 && Math.abs(diff) >= 100) {
        pct = Math.round((Math.abs(diff) / fav.ultimo_precio_guardado) * 100);
        if (diff < 0) {
          tipo = 'BAJO';
        } else if (diff > 0) {
          tipo = 'SUBIO';
        }
      }

      const volvioDisponible = fav.ultimo_stock_disponible === false && Boolean(disponibleActual);

      return {
        ...fav,
        precio_actual: precioActual,
        precio_kilo_actual: precioKiloActual,
        disponible_actual: disponibleActual,
        diferencia_precio: diff,
        porcentaje_variacion: pct,
        tipo_variacion: tipo,
        volvio_disponible: volvioDisponible,
      };
    });
  }
}
