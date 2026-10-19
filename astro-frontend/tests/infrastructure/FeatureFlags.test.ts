import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { FeatureFlags } from '../../src/core/infrastructure/config/FeatureFlags';
import { Environment } from '../../src/core/infrastructure/config/Environment';

describe('FeatureFlags & Environment (Estrategia de Lanzamiento Controlado)', () => {
  const originalEnv = { ...import.meta.env };

  afterEach(() => {
    // Restaurar entorno
    vi.unstubAllEnvs();
  });

  it('habilita por defecto guías y calibrador si no se especifican variables', () => {
    vi.stubEnv('PUBLIC_ENABLE_RECIPES', undefined as any);
    vi.stubEnv('ENABLE_RECIPES', undefined as any);
    vi.stubEnv('PUBLIC_ENABLE_CALIBRATOR', undefined as any);
    vi.stubEnv('ENABLE_CALIBRATOR', undefined as any);

    expect(FeatureFlags.isGuidesEnabled()).toBe(true);
    expect(FeatureFlags.isCalibratorEnabled()).toBe(true);
    expect(Environment.isGuidesEnabled()).toBe(true);
    expect(Environment.isCalibratorEnabled()).toBe(true);
  });

  it('deshabilita guías cuando PUBLIC_ENABLE_RECIPES=false', () => {
    vi.stubEnv('PUBLIC_ENABLE_RECIPES', 'false');
    expect(FeatureFlags.isGuidesEnabled()).toBe(false);
    expect(Environment.isGuidesEnabled()).toBe(false);
  });

  it('deshabilita calibrador cuando ENABLE_CALIBRATOR=0', () => {
    vi.stubEnv('PUBLIC_ENABLE_CALIBRATOR', undefined as any);
    vi.stubEnv('ENABLE_CALIBRATOR', '0');
    expect(FeatureFlags.isCalibratorEnabled()).toBe(false);
    expect(Environment.isCalibratorEnabled()).toBe(false);
  });

  it('retorna snapshot completo con getAll()', () => {
    vi.stubEnv('PUBLIC_ENABLE_RECIPES', 'true');
    vi.stubEnv('PUBLIC_ENABLE_CALIBRATOR', 'false');

    const flags = FeatureFlags.getAll();
    expect(flags.guides).toBe(true);
    expect(flags.calibrator).toBe(false);
    expect(flags.myRecipes).toBe(true);
  });
});

