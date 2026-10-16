import { describe, it, expect } from 'vitest';
import { Recipe } from '../../src/core/domain/models/Recipe';

describe('Recipe Entity (CU-08)', () => {
  it('calcula ratio café:agua con un decimal de precisión', () => {
    const recipe = new Recipe({
      id: 'rec-1',
      cafe: 'Etiopía Yirgacheffe',
      metodo: 'V60',
      gramos_cafe: 15,
      gramos_agua: 250,
      calificacion: 5,
      fecha: '2026-10-15T12:00:00Z'
    });

    expect(recipe.getRatio()).toBe('1:16.7');
  });

  it('asegura rangos mínimos físicos de agua y café', () => {
    const recipe = new Recipe({
      id: 'rec-2',
      cafe: 'Prueba',
      metodo: 'Espresso',
      gramos_cafe: 0,
      gramos_agua: -50,
      calificacion: 10,
      fecha: '2026-10-15T12:00:00Z'
    });

    expect(recipe.gramos_cafe).toBe(1);
    expect(recipe.gramos_agua).toBe(10);
    expect(recipe.calificacion).toBe(5); // Clamped to 5
  });
});

