import { describe, it, expect } from 'vitest';
import { COFFEE_ANATOMY_LAYERS, getAnatomyLayerById } from '../../src/core/domain/coffeeAnatomyData';

describe('CoffeeAnatomyData Domain', () => {
  it('debe contener exactamente las 7 capas anatómicas del grano y cereza de café', () => {
    expect(COFFEE_ANATOMY_LAYERS).toHaveLength(7);
  });

  it('cada capa debe tener campos obligatorios completos y válidos', () => {
    COFFEE_ANATOMY_LAYERS.forEach(layer => {
      expect(layer.id).toBeTruthy();
      expect(layer.numero).toBeGreaterThanOrEqual(1);
      expect(layer.numero).toBeLessThanOrEqual(7);
      expect(layer.nombreComun).toBeTruthy();
      expect(layer.nombreBotanico).toBeTruthy();
      expect(layer.colorHex).toMatch(/^#[0-9A-Fa-f]{6}$/);
      expect(layer.colorGradiente).toHaveLength(2);
      expect(layer.resumen.length).toBeGreaterThan(20);
      expect(layer.rolBiologico.length).toBeGreaterThan(20);
      expect(layer.impactoEnTaza.length).toBeGreaterThan(20);
      expect(layer.procesosRelacionados.length).toBeGreaterThan(0);
      expect(layer.atributosQuimicos.length).toBeGreaterThan(0);
    });
  });

  it('debe recuperar capas correctamente mediante getAnatomyLayerById', () => {
    const exocarpio = getAnatomyLayerById('exocarpio');
    expect(exocarpio).toBeDefined();
    expect(exocarpio?.nombreBotanico).toContain('Exocarpio');

    const endospermo = getAnatomyLayerById('endospermo');
    expect(endospermo).toBeDefined();
    expect(endospermo?.nombreComun).toContain('Grano Verde');

    const inexistente = getAnatomyLayerById('capa-fantasma');
    expect(inexistente).toBeUndefined();
  });

  it('todas las capas deben tener un slug de término de glosario asignado para anclaje', () => {
    COFFEE_ANATOMY_LAYERS.forEach(layer => {
      expect(layer.terminoGlosarioSlug).toBeDefined();
      expect(typeof layer.terminoGlosarioSlug).toBe('string');
    });
  });
});
