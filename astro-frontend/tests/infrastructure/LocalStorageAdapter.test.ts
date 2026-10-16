import { describe, it, expect, beforeEach } from 'vitest';
import { LocalStorageAdapter } from '../../src/core/infrastructure/storage/LocalStorageAdapter';
import { Recipe } from '../../src/core/domain/models/Recipe';

describe('LocalStorageAdapter (CU-08 & CU-10)', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('mantiene un máximo de 5 productos en Vistos Recientemente (FIFO)', () => {
    for (let i = 1; i <= 7; i++) {
      LocalStorageAdapter.addRecentlyViewed({
        id: i,
        nombre: `Café ${i}`,
        tienda: 'Tienda Test',
        precio: i * 5000
      });
    }

    const list = LocalStorageAdapter.getRecentlyViewed();
    expect(list.length).toBe(5);
    // El último agregado debe estar al inicio
    expect(list[0].id).toBe(7);
    expect(list[4].id).toBe(3);
  });

  it('evita duplicados moviendo el producto al frente de la lista', () => {
    LocalStorageAdapter.addRecentlyViewed({ id: 1, nombre: 'Café 1', tienda: 'T', precio: 1000 });
    LocalStorageAdapter.addRecentlyViewed({ id: 2, nombre: 'Café 2', tienda: 'T', precio: 2000 });
    LocalStorageAdapter.addRecentlyViewed({ id: 1, nombre: 'Café 1 Revisitado', tienda: 'T', precio: 1000 });

    const list = LocalStorageAdapter.getRecentlyViewed();
    expect(list.length).toBe(2);
    expect(list[0].id).toBe(1);
    expect(list[1].id).toBe(2);
  });

  it('persiste y recupera recetas de la bitácora local-first', () => {
    const recipe = new Recipe({
      id: 'rec-test-1',
      cafe: 'Geisha Anaeróbico',
      metodo: 'Aeropress',
      gramos_cafe: 18,
      gramos_agua: 200,
      calificacion: 5,
      fecha: '2026-10-15T00:00:00Z'
    });

    LocalStorageAdapter.saveRecipe(recipe);
    const saved = LocalStorageAdapter.getRecipes();

    expect(saved.length).toBe(1);
    expect(saved[0].cafe).toBe('Geisha Anaeróbico');
    expect(saved[0].getRatio()).toBe('1:11.1');

    // Eliminar receta
    const afterDelete = LocalStorageAdapter.deleteRecipe('rec-test-1');
    expect(afterDelete.length).toBe(0);
    expect(LocalStorageAdapter.getRecipes().length).toBe(0);
  });

  it('genera y persiste un deviceId anónimo único', () => {
    const id1 = LocalStorageAdapter.getDeviceId();
    const id2 = LocalStorageAdapter.getDeviceId();

    expect(id1).toBeDefined();
    expect(id1.startsWith('dev-')).toBe(true);
    expect(id1).toBe(id2);
  });
});

