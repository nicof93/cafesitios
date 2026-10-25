/**
 * coffeeAnatomyData.ts
 * Dominio de datos botánicos y estructurales del grano y la cereza de café.
 * Modela las 7 capas anatómicas concéntricas con sus funciones biológicas,
 * impacto en taza y vínculos a conceptos del Glosario.
 */

export interface CoffeeAnatomyLayer {
  id: string;
  numero: number;
  nombreComun: string;
  nombreBotanico: string;
  colorHex: string;
  colorGradiente: [string, string];
  icono: string;
  resumen: string;
  rolBiologico: string;
  impactoEnTaza: string;
  procesosRelacionados: string[];
  terminoGlosarioSlug?: string;
  atributosQuimicos: string[];
}

export const COFFEE_ANATOMY_LAYERS: CoffeeAnatomyLayer[] = [
  {
    id: 'exocarpio',
    numero: 1,
    nombreComun: 'Piel Exterior / Cáscara',
    nombreBotanico: 'Exocarpio (Epicarpio)',
    colorHex: '#DC2626',
    colorGradiente: ['#EF4444', '#991B1B'],
    icono: '🍒',
    resumen: 'Capa externa monocelular brillante que protege el fruto de la radiación UV, insectos y hongos.',
    rolBiologico: 'Barrera protectora epidérmica rica en clorofila y luego en antocianinas y carotenoides que otorgan el color rojo rubí o amarillo oro al madurar.',
    impactoEnTaza: 'En el proceso Natural se seca con ella puesta, aportando cuerpo licoroso, notas a ciruela madura y frutos secos. Si se retira, su pulpa se seca por separado para producir la infusión de Cáscara (tisana herbal dulce).',
    procesosRelacionados: ['Proceso Natural', 'Infusión de Cáscara', 'Maduración Óptima'],
    terminoGlosarioSlug: 'proceso-natural',
    atributosQuimicos: ['Antocianinas', 'Polifenoles', 'Taninos', 'Pectinas']
  },
  {
    id: 'mesocarpio',
    numero: 2,
    nombreComun: 'Pulpa & Mucílago',
    nombreBotanico: 'Mesocarpio',
    colorHex: '#F59E0B',
    colorGradiente: ['#FBBF24', '#D97706'],
    icono: '🍯',
    resumen: 'Capa carnosa gelatinosa, intensamente dulce y pegajosa que envuelve directamente a las semillas.',
    rolBiologico: 'Tejido parenquimático esponjoso cargado de agua y azúcares fermentables que sirven de combustible biológico durante el crecimiento del fruto.',
    impactoEnTaza: 'Es el corazón de los cafés Honey: el porcentaje de mucílago dejado durante el secado define las categorías Yellow (25%), Red (50%) o Black Honey (100%), impartiendo dulzura melosa, sensación sedosa en boca y acidez jugosa.',
    procesosRelacionados: ['Proceso Honey', 'Maceración Carbónica', 'Fermentación Anaeróbica'],
    terminoGlosarioSlug: 'proceso-honey',
    atributosQuimicos: ['Glucosa', 'Fructosa', 'Ácido Cítrico y Málico', 'Pectinas Solubles']
  },
  {
    id: 'endocarpio',
    numero: 3,
    nombreComun: 'Pergamino / Cascarilla',
    nombreBotanico: 'Endocarpio (Parchment)',
    colorHex: '#D97706',
    colorGradiente: ['#FDE68A', '#B45309'],
    icono: '📜',
    resumen: 'Cáscara dura, rugosa y apergaminada de color marfil que forma la armadura protectora del grano.',
    rolBiologico: 'Capa esclerotizada formada por células muertas endurecidas de lignina que aíslan la semilla verde de la intemperie y regulan la pérdida de humedad.',
    impactoEnTaza: 'En el proceso Lavado, el café se lava completamente y se seca dentro de este pergamino. El café de especialidad reposa semanas en pergamino ("reposo en bodega") para estabilizar su humedad entre 10% y 11.5% antes del trillado final.',
    procesosRelacionados: ['Proceso Lavado', 'Trillado (Hulling)', 'Reposo en Pergamino'],
    terminoGlosarioSlug: 'proceso-lavado',
    atributosQuimicos: ['Lignina (43%)', 'Celulosa (35%)', 'Polisacáridos Insolubles']
  },
  {
    id: 'espermoderma',
    numero: 4,
    nombreComun: 'Película Plateada',
    nombreBotanico: 'Espermoderma (Silverskin)',
    colorHex: '#94A3B8',
    colorGradiente: ['#E2E8F0', '#64748B'],
    icono: '✨',
    resumen: 'Membrana finísima, translúcida y brillante adherida con tenacidad a la superficie del grano verde.',
    rolBiologico: 'Última envoltura seminal que protege el embrión y los cotiledones de la humedad exterior inmediata.',
    impactoEnTaza: 'Durante el tueste, a medida que el grano se expande en el "Primer Crack", esta película se seca y se desprende en copos voladores llamados "chaff" o cascarilla. Si queda exceso en el surco central puede aportar un ligero amargor a ceniza si no se aspira bien.',
    procesosRelacionados: ['Primer Crack', 'Desarrollo del Tueste', 'Aspiración de Chaff'],
    terminoGlosarioSlug: 'desarrollo-tueste',
    atributosQuimicos: ['Fibra Dietaria (60%)', 'Ácido Clorogénico', 'Compuestos Fenólicos']
  },
  {
    id: 'endospermo',
    numero: 5,
    nombreComun: 'Semilla / Grano Verde',
    nombreBotanico: 'Endospermo',
    colorHex: '#10B981',
    colorGradiente: ['#34D399', '#047857'],
    icono: '🌱',
    resumen: 'El grano de café propiamente dicho: tejido denso de almacenamiento de nutrientes con tono verde azulado.',
    rolBiologico: 'Reserva celular repleta de sacarosa, lípidos, cafeína, minerales y aminoácidos destinados a nutrir la plántula al germinar.',
    impactoEnTaza: 'Determina el 100% del potencial sensorial en taza. Sus precursores químicos reaccionan bajo la reacción de Maillard y caramelización durante el tueste para liberar los 800+ compuestos volátiles aromáticos (jazmín, chocolate, caramelo, frutas).',
    procesosRelacionados: ['Puntaje SCA', 'Densidad de Altura', 'Variedad Geisha / Bourbon'],
    terminoGlosarioSlug: 'puntaje-sca',
    atributosQuimicos: ['Sacarosa (6-9%)', 'Cafeína (1-1.5%)', 'Ácidos Clorogénicos (7-10%)', 'Trigonelina']
  },
  {
    id: 'surcoCentral',
    numero: 6,
    nombreComun: 'Surco Central / Hendidura',
    nombreBotanico: 'Rafe / Hendidura Central (Center Cut)',
    colorHex: '#475569',
    colorGradiente: ['#64748B', '#1E293B'],
    icono: '〰️',
    resumen: 'Ranura longitudinal característica en la cara plana del grano donde las dos semillas se tocan.',
    rolBiologico: 'Punto de sutura y alimentación vascular por donde el grano recibe agua y solutos desde la planta madre.',
    impactoEnTaza: 'Los tostadores profesionales observan el surco central para verificar si el tueste fue homogéneo hasta el corazón del grano. Si el surco permanece cerrado o pálido indica tueste disparejo o subdesarrollado (astringente / cereal crudo).',
    procesosRelacionados: ['Escala Agtron', 'Desarrollo del Tueste', 'Evaluación Visual'],
    terminoGlosarioSlug: 'escala-agtron',
    atributosQuimicos: ['Residuos de Silverskin', 'Fibras Vasculares Lignificadas']
  },
  {
    id: 'embrion',
    numero: 7,
    nombreComun: 'Embrión',
    nombreBotanico: 'Eje Embrionario (Embryo)',
    colorHex: '#FBBF24',
    colorGradiente: ['#FDE047', '#D97706'],
    icono: '⚡',
    resumen: 'La chispa germinal viva de apenas 3-4 mm ubicada en la base dorsal del grano.',
    rolBiologico: 'Contiene los cotiledones y la radícula que dan vida a un nuevo cafeto si se siembra en vivero.',
    impactoEnTaza: 'Si el grano verde es sobrecalentado o almacenado con humedad excesiva, el embrión muere, provocando que los lípidos se oxiden rápidamente y el café adquiera gusto a paja, yute viejo o madera seca (café viejo o past-crop).',
    procesosRelacionados: ['Fisiología del Café', 'Almacenamiento Specialty', 'Empaque GrainPro'],
    terminoGlosarioSlug: 'terroir',
    atributosQuimicos: ['ADN Vegetal', 'Lípidos Insaturados', 'Enzimas Germinales']
  }
];

export function getAnatomyLayerById(id: string): CoffeeAnatomyLayer | undefined {
  return COFFEE_ANATOMY_LAYERS.find(layer => layer.id === id);
}
