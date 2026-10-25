import { describe, it, expect } from 'vitest';
import { GLOSSARY_TERMS, GLOSSARY_CATEGORIES, searchGlossaryTerms } from '../../src/core/domain/glossaryData';

describe('Glosario de Café de Especialidad (Domain)', () => {
  it('contiene los 28 términos esenciales iniciales', () => {
    expect(GLOSSARY_TERMS.length).toBeGreaterThanOrEqual(28);
  });

  it('clasifica los términos en las 5 categorías canónicas', () => {
    expect(GLOSSARY_CATEGORIES).toHaveLength(5);
    const categoryIds = GLOSSARY_CATEGORIES.map(c => c.id);

    GLOSSARY_TERMS.forEach(term => {
      expect(categoryIds).toContain(term.categoria);
      expect(term.slug).toBeTruthy();
      expect(term.termino).toBeTruthy();
      expect(term.resumen).toBeTruthy();
      expect(term.explicacion).toBeTruthy();
      expect(term.impactoEnTaza).toBeTruthy();
      expect(term.icono).toBeTruthy();
    });
  });

  it('filtra términos por búsqueda de texto parcial de forma insensible a mayúsculas', () => {
    const resultsHoney = searchGlossaryTerms('honey');
    expect(resultsHoney.length).toBeGreaterThanOrEqual(1);
    expect(resultsHoney.some(t => t.slug === 'proceso-honey')).toBe(true);

    const resultsAgtron = searchGlossaryTerms('AGTRON');
    expect(resultsAgtron.length).toBeGreaterThanOrEqual(1);
    expect(resultsAgtron.some(t => t.slug === 'escala-agtron')).toBe(true);
  });

  it('filtra términos por categoría específica', () => {
    const procesos = searchGlossaryTerms('', 'procesos');
    expect(procesos.length).toBeGreaterThanOrEqual(5);
    expect(procesos.every(t => t.categoria === 'procesos')).toBe(true);

    const botanica = searchGlossaryTerms('', 'botanica');
    expect(botanica.length).toBeGreaterThanOrEqual(5);
    expect(botanica.every(t => t.categoria === 'botanica')).toBe(true);
  });

  it('combina búsqueda por categoría y palabra clave simultáneamente', () => {
    const geishaBotanica = searchGlossaryTerms('geisha', 'botanica');
    expect(geishaBotanica).toHaveLength(1);
    expect(geishaBotanica[0].slug).toBe('variedad-geisha');

    const geishaTueste = searchGlossaryTerms('geisha', 'tueste');
    expect(geishaTueste).toHaveLength(0);
  });
});
