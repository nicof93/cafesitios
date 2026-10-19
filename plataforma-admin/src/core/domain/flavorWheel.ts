export interface FlavorMacroFamily {
  id: string;
  nombre: string;
  color: string;
  colorFondo: string;
  colorBorde: string;
  colorTexto: string;
  icono: string;
  notas: string[];
}

export const SCA_FLAVOR_WHEEL_DATA: FlavorMacroFamily[] = [
  {
    id: 'floral',
    nombre: 'Floral',
    color: '#8B5CF6',
    colorFondo: '#F5F3FF',
    colorBorde: '#DDD6FE',
    colorTexto: '#6D28D9',
    icono: '🌸',
    notas: [
      'Floral',
      'Jazmín',
      'Flor blanca',
      'Azahar',
      'Rosa',
      'Lavanda',
      'Manzanilla',
      'Hibisco',
      'Té negro',
      'Té verde',
      'Bergamota',
      'Magnolia'
    ]
  },
  {
    id: 'citrico',
    nombre: 'Frutal / Cítrico',
    color: '#F59E0B',
    colorFondo: '#FFFBEB',
    colorBorde: '#FDE68A',
    colorTexto: '#B45309',
    icono: '🍋',
    notas: [
      'Cítrico',
      'Limón',
      'Lima',
      'Naranja',
      'Mandarina',
      'Pomelo',
      'Clementina',
      'Manzana verde',
      'Cidra',
      'Hierba luisa'
    ]
  },
  {
    id: 'frutos_rojos',
    nombre: 'Frutal / Frutos Rojos',
    color: '#E11D48',
    colorFondo: '#FFF1F2',
    colorBorde: '#FECDD3',
    colorTexto: '#BE123C',
    icono: '🍓',
    notas: [
      'Frutos rojos',
      'Frutilla',
      'Frambuesa',
      'Arándano',
      'Cereza',
      'Mora',
      'Grosella',
      'Ciruela',
      'Granada',
      'Casis',
      'Uva',
      'Vino'
    ]
  },
  {
    id: 'dulce_chocolate',
    nombre: 'Dulce / Chocolate',
    color: '#B45309',
    colorFondo: '#FEF3C7',
    colorBorde: '#FDE68A',
    colorTexto: '#92400E',
    icono: '🍫',
    notas: [
      'Caramelo',
      'Chocolate',
      'Cacao',
      'Panela',
      'Miel',
      'Vainilla',
      'Chocolate amargo',
      'Chocolate con leche',
      'Toffee',
      'Dulce de leche',
      'Azúcar morena',
      'Melaza',
      'Butterscotch',
      'Praliné'
    ]
  },
  {
    id: 'frutos_secos',
    nombre: 'Frutos Secos',
    color: '#059669',
    colorFondo: '#ECFDF5',
    colorBorde: '#A7F3D0',
    colorTexto: '#047857',
    icono: '🥜',
    notas: [
      'Frutos secos',
      'Almendra',
      'Nuez',
      'Avellana',
      'Maní',
      'Castaña',
      'Pistacho',
      'Pecana',
      'Nuez de macadamia'
    ]
  }
];

export function sanitizeNote(str: string): string {
  if (!str) return '';
  return str
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .trim();
}

export interface MatchedNoteInfo {
  canonicalName: string;
  familyId: string;
  familyName: string;
  color: string;
  isMatched: boolean;
}

export function matchProductNotesToWheel(productNotes: string[]): {
  wheelFamilies: {
    family: FlavorMacroFamily;
    activeNotesCount: number;
    notes: {
      name: string;
      isActive: boolean;
    }[];
  }[];
  activeFamilies: FlavorMacroFamily[];
  unmatchedNotes: string[];
} {
  const sanitizedProductNotes = productNotes.map(n => sanitizeNote(n));

  const unmatchedSet = new Set(productNotes);

  const wheelFamilies = SCA_FLAVOR_WHEEL_DATA.map(family => {
    let activeNotesCount = 0;
    const notes = family.notas.map(canonical => {
      const sanitizedCanon = sanitizeNote(canonical);
      // Coincidencia exacta o por inclusión de subcadena
      const matched = sanitizedProductNotes.some(pn => {
        if (!pn) return false;
        return pn === sanitizedCanon || pn.includes(sanitizedCanon) || sanitizedCanon.includes(pn);
      });

      if (matched) {
        activeNotesCount++;
        // Retirar de notas no emparejadas
        productNotes.forEach(orig => {
          if (sanitizeNote(orig).includes(sanitizedCanon) || sanitizedCanon.includes(sanitizeNote(orig))) {
            unmatchedSet.delete(orig);
          }
        });
      }

      return {
        name: canonical,
        isActive: matched
      };
    });

    return {
      family,
      activeNotesCount,
      notes
    };
  });

  const activeFamilies = wheelFamilies
    .filter(wf => wf.activeNotesCount > 0)
    .map(wf => wf.family);

  return {
    wheelFamilies,
    activeFamilies,
    unmatchedNotes: Array.from(unmatchedSet)
  };
}

