import { Recipe, type RecipeProps } from '../../domain/models/Recipe';

export interface RecentlyViewedItem {
  id: number;
  nombre: string;
  tienda: string;
  precio: number;
  imagen?: string;
  url_detalle?: string;
  fecha?: string;
}

export class LocalStorageAdapter {
  private static readonly KEY_RECENTLY_VIEWED = 'cafesitios_vistos_recientemente_v1';
  private static readonly KEY_RECIPES = 'cafesitios_recetas_v1';
  private static readonly KEY_DEVICE_ID = 'cafesitios_device_id';

  // --- DEVICE ID ---
  static getDeviceId(): string {
    if (typeof window === 'undefined') return 'server-context';
    let id = localStorage.getItem(this.KEY_DEVICE_ID);
    if (!id) {
      id = 'dev-' + Math.random().toString(36).substring(2, 15) + '-' + Date.now();
      localStorage.setItem(this.KEY_DEVICE_ID, id);
    }
    return id;
  }

  // --- RECENTLY VIEWED (CU-10) ---
  static getRecentlyViewed(): RecentlyViewedItem[] {
    if (typeof window === 'undefined') return [];
    try {
      const raw = localStorage.getItem(this.KEY_RECENTLY_VIEWED);
      return raw ? JSON.parse(raw) : [];
    } catch {
      return [];
    }
  }

  static addRecentlyViewed(item: RecentlyViewedItem): void {
    if (typeof window === 'undefined') return;
    try {
      const list = this.getRecentlyViewed().filter(p => p.id !== item.id);
      list.unshift({ ...item, fecha: new Date().toISOString() });
      const capped = list.slice(0, 5);
      localStorage.setItem(this.KEY_RECENTLY_VIEWED, JSON.stringify(capped));
    } catch (err) {
      console.error('Error guardando en vistos recientemente:', err);
    }
  }

  static clearRecentlyViewed(): void {
    if (typeof window === 'undefined') return;
    localStorage.removeItem(this.KEY_RECENTLY_VIEWED);
  }

  // --- RECIPES (CU-08) ---
  static getRecipes(): Recipe[] {
    if (typeof window === 'undefined') return [];
    try {
      const raw = localStorage.getItem(this.KEY_RECIPES);
      const list: RecipeProps[] = raw ? JSON.parse(raw) : [];
      return list.map(r => new Recipe(r));
    } catch {
      return [];
    }
  }

  static saveRecipe(recipe: Recipe): Recipe[] {
    if (typeof window === 'undefined') return [];
    try {
      const recipes = this.getRecipes();
      recipes.unshift(recipe);
      localStorage.setItem(this.KEY_RECIPES, JSON.stringify(recipes));
      return recipes;
    } catch (err) {
      console.error('Error guardando receta:', err);
      return this.getRecipes();
    }
  }

  static deleteRecipe(id: string): Recipe[] {
    if (typeof window === 'undefined') return [];
    try {
      const filtered = this.getRecipes().filter(r => r.id !== id);
      localStorage.setItem(this.KEY_RECIPES, JSON.stringify(filtered));
      return filtered;
    } catch (err) {
      console.error('Error eliminando receta:', err);
      return this.getRecipes();
    }
  }

  static clearRecipes(): void {
    if (typeof window === 'undefined') return;
    localStorage.removeItem(this.KEY_RECIPES);
  }
}

