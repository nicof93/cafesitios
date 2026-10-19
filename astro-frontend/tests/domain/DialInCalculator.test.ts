import { describe, it, expect } from 'vitest';
import { DialInCalculator, DIAL_IN_METHODS } from '../../src/core/domain/DialInCalculator';

describe('DialInCalculator Domain Service', () => {
  it('contiene los 5 métodos base requeridos con parámetros predeterminados coherentes', () => {
    expect(DIAL_IN_METHODS['v60']).toBeDefined();
    expect(DIAL_IN_METHODS['aeropress']).toBeDefined();
    expect(DIAL_IN_METHODS['espresso']).toBeDefined();
    expect(DIAL_IN_METHODS['moka']).toBeDefined();
    expect(DIAL_IN_METHODS['prensa']).toBeDefined();

    expect(DIAL_IN_METHODS['v60'].dosis).toBe(15);
    expect(DIAL_IN_METHODS['espresso'].dosis).toBe(18);
    expect(DIAL_IN_METHODS['prensa'].dosis).toBe(20);
  });

  it('identifica correctamente la "Zona Ideal" cuando |X| <= 0.2 y |Y| <= 0.2', () => {
    const input = {
      metodo: 'v60',
      dosis: 15,
      agua: 240,
      clicks: 18,
      temperatura: 93,
      tiempo: 180,
      x: 0.1,
      y: -0.15
    };

    const resultado = DialInCalculator.calculate(input);

    expect(resultado.zonaIdeal).toBe(true);
    expect(resultado.cuadrante).toContain('Zona Ideal');
    expect(resultado.deltaClicks).toBe(0);
    expect(resultado.deltaRatio).toBe(0);
    expect(resultado.deltaTemperatura).toBe(0);
    expect(resultado.deltaTiempo).toBe(0);
    expect(resultado.ratioSugerido).toBe(resultado.ratioActual);
  });

  it('corrige la Subextracción (X < -0.2) sugiriendo molienda más fina, mayor temperatura y tiempo', () => {
    const input = {
      metodo: 'v60',
      dosis: 15,
      agua: 240,
      clicks: 18,
      temperatura: 92,
      tiempo: 180,
      x: -0.6, // Muy subextraído / ácido
      y: 0.0 // Concentración ideal
    };

    const resultado = DialInCalculator.calculate(input);

    expect(resultado.zonaIdeal).toBe(false);
    expect(resultado.deltaClicks).toBeLessThan(0); // clicks más finos
    expect(resultado.clicksSugeridos).toBeLessThan(input.clicks);
    expect(resultado.deltaTemperatura).toBeGreaterThan(0); // sube temp
    expect(resultado.temperaturaSugerida).toBeGreaterThan(input.temperatura);
    expect(resultado.deltaTiempo).toBeGreaterThan(0); // alarga tiempo de contacto
    expect(resultado.pasosTacticos.length).toBeGreaterThan(0);
    expect(resultado.pasosTacticos[0]).toContain('FINO');
  });

  it('corrige la Sobreextracción (X > 0.2) sugiriendo molienda más gruesa y menor temperatura', () => {
    const input = {
      metodo: 'aeropress',
      dosis: 15,
      agua: 220,
      clicks: 14,
      temperatura: 92,
      tiempo: 120,
      x: 0.7, // Sobreextraído / amargo seco
      y: 0.0
    };

    const resultado = DialInCalculator.calculate(input);

    expect(resultado.zonaIdeal).toBe(false);
    expect(resultado.deltaClicks).toBeGreaterThan(0); // clicks más gruesos
    expect(resultado.clicksSugeridos).toBeGreaterThan(input.clicks);
    expect(resultado.deltaTemperatura).toBeLessThan(0); // baja temp
    expect(resultado.temperaturaSugerida).toBeLessThan(input.temperatura);
    expect(resultado.pasosTacticos[0]).toContain('GRUESO');
  });

  it('corrige la Concentración Alta / Saturada (Y > 0.2) abriendo el ratio (más agua)', () => {
    const input = {
      metodo: 'v60',
      dosis: 15,
      agua: 225, // ratio 1:15
      clicks: 18,
      temperatura: 93,
      tiempo: 180,
      x: 0.0,
      y: 0.6, // Pesado / Saturado
      modoAjuste: 'agua' as const
    };

    const resultado = DialInCalculator.calculate(input);

    expect(resultado.zonaIdeal).toBe(false);
    expect(resultado.deltaRatio).toBeGreaterThan(0); // abrir ratio
    expect(resultado.ratioSugerido).toBeGreaterThan(resultado.ratioActual);
    expect(resultado.deltaAgua).toBeGreaterThan(0); // sube agua
    expect(resultado.aguaSugerida).toBeGreaterThan(input.agua);
  });

  it('corrige la Concentración Baja / Acuosa (Y < -0.2) cerrando el ratio (menos agua o más café)', () => {
    const input = {
      metodo: 'v60',
      dosis: 15,
      agua: 255, // ratio 1:17
      clicks: 18,
      temperatura: 93,
      tiempo: 180,
      x: 0.0,
      y: -0.6, // Acuoso
      modoAjuste: 'dosis' as const
    };

    const resultado = DialInCalculator.calculate(input);

    expect(resultado.zonaIdeal).toBe(false);
    expect(resultado.deltaRatio).toBeLessThan(0); // cerrar ratio
    expect(resultado.ratioSugerido).toBeLessThan(resultado.ratioActual);
    expect(resultado.deltaDosis).toBeGreaterThan(0); // más dosis para compensar
    expect(resultado.dosisSugerida).toBeGreaterThan(input.dosis);
  });

  it('maneja cuadrante combinado subextraído + acuoso (X < -0.2, Y < -0.2)', () => {
    const input = {
      metodo: 'prensa',
      dosis: 20,
      agua: 320,
      clicks: 24,
      temperatura: 93,
      tiempo: 270,
      x: -0.5,
      y: -0.5
    };

    const resultado = DialInCalculator.calculate(input);

    expect(resultado.cuadrante).toBe('Subextraído y Acuoso');
    expect(resultado.deltaClicks).toBeLessThan(0);
    expect(resultado.deltaRatio).toBeLessThan(0);
    expect(resultado.descriptorSabor).toContain('Ácido hueco');
  });

  it('protege rangos contra valores extremos (clamping seguro)', () => {
    const input = {
      metodo: 'v60',
      dosis: -5, // extremo inválido
      agua: 0,
      clicks: -2,
      temperatura: 120, // fuera de rango
      tiempo: -10,
      x: -2.5, // fuera de [-1, 1]
      y: 3.0
    };

    const resultado = DialInCalculator.calculate(input);

    expect(resultado).toBeDefined();
    expect(resultado.clicksSugeridos).toBeGreaterThan(0);
    expect(resultado.temperaturaSugerida).toBeLessThanOrEqual(96);
    expect(resultado.ratioSugerido).toBeGreaterThanOrEqual(1.5);
  });
});

