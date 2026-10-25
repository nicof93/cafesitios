export type GlossaryCategory = 'procesos' | 'botanica' | 'tueste' | 'cata' | 'extraccion';

export interface GlossaryTerm {
  slug: string;
  termino: string;
  categoria: GlossaryCategory;
  categoriaNombre: string;
  icono: string;
  resumen: string;
  explicacion: string;
  impactoEnTaza: string;
  filtroCatalogoQuery?: string;
  terminosRelacionados?: string[];
}

export const GLOSSARY_CATEGORIES: { id: GlossaryCategory; nombre: string; icono: string; descripcion: string }[] = [
  {
    id: 'procesos',
    nombre: 'Procesos & Fermentación',
    icono: '⚙️',
    descripcion: 'Técnicas de beneficio y fermentación poscosecha para separar la pulpa del grano.'
  },
  {
    id: 'botanica',
    nombre: 'Botánica & Origen',
    icono: '🌱',
    descripcion: 'Variedades genéticas del café, altitud de cultivo y condiciones de terroir.'
  },
  {
    id: 'tueste',
    nombre: 'Tueste & Colorimetría',
    icono: '🔥',
    descripcion: 'Curvas de tostado, desarrollo térmico y escalas internacionales de color.'
  },
  {
    id: 'cata',
    nombre: 'Cata & Estándar SCA',
    icono: '☕',
    descripcion: 'Protocolo internacional de catación, puntajes Q-Grader y rueda sensorial de sabores.'
  },
  {
    id: 'extraccion',
    nombre: 'Preparación & Extracción',
    icono: '⚖️',
    descripcion: 'Variables físicas y químicas para preparar la taza perfecta en cada método.'
  }
];

export const GLOSSARY_TERMS: GlossaryTerm[] = [
  // =========================================================================
  // 1. PROCESOS & FERMENTACIÓN
  // =========================================================================
  {
    slug: 'proceso-lavado',
    termino: 'Proceso Lavado (Washed)',
    categoria: 'procesos',
    categoriaNombre: 'Procesos & Fermentación',
    icono: '💧',
    resumen: 'Se retira toda la cáscara y el mucílago pegajoso con agua y fermentación antes de secar el grano.',
    explicacion: 'Es el proceso tradicional más riguroso y limpio. Las cerezas se despulpan el mismo día de la cosecha, se fermentan en tanques para desintegrar el mucílago y se lavan con agua limpia antes de pasar a camas de secado.',
    impactoEnTaza: 'Tazas sumamente limpias, brillantes, con alta acidez cítrica y expresión pura del terroir y la variedad sin notas fermentadas.',
    filtroCatalogoQuery: 'proceso=Lavado',
    terminosRelacionados: ['proceso-natural', 'proceso-honey', 'terroir']
  },
  {
    slug: 'proceso-natural',
    termino: 'Proceso Natural (Seco)',
    categoria: 'procesos',
    categoriaNombre: 'Procesos & Fermentación',
    icono: '☀️',
    resumen: 'La cereza de café se seca entera al sol con su pulpa y azúcares durante semanas.',
    explicacion: 'El método más antiguo de beneficio. Las cerezas maduras recolectadas se extienden en camas africanas o patios solares sin retirar la pulpa, permitiendo que los azúcares y levaduras naturales migren al grano durante el secado.',
    impactoEnTaza: 'Gran cuerpo y textura almibarada, dulzura intensa y notas muy marcadas a frutas maduras, frutillas, arándanos o vino.',
    filtroCatalogoQuery: 'proceso=Natural',
    terminosRelacionados: ['proceso-lavado', 'proceso-honey', 'fermentacion-anaerobica']
  },
  {
    slug: 'proceso-honey',
    termino: 'Proceso Honey (Miel)',
    categoria: 'procesos',
    categoriaNombre: 'Procesos & Fermentación',
    icono: '🍯',
    resumen: 'Híbrido entre lavado y natural: se quita la piel pero se seca el grano con su mucílago dulce.',
    explicacion: 'Originario de Costa Rica. Se despulpa la cereza pero no se lava, dejando una capa de mucílago viscoso que parece miel. Según el porcentaje de mucílago restante y la exposición a sombra/sol se clasifica en Yellow Honey, Red Honey o Black Honey.',
    impactoEnTaza: 'Dulzura cremosa y notas a miel, caña de azúcar, durazno y fruta de hueso, combinando la claridad del lavado con el cuerpo del natural.',
    filtroCatalogoQuery: 'proceso=Honey',
    terminosRelacionados: ['proceso-lavado', 'proceso-natural']
  },
  {
    slug: 'fermentacion-anaerobica',
    termino: 'Fermentación Anaeróbica',
    categoria: 'procesos',
    categoriaNombre: 'Procesos & Fermentación',
    icono: '🧪',
    resumen: 'El café se fermenta en tanques sellados herméticamente sin presencia de oxígeno.',
    explicacion: 'Al purgar el oxígeno con válvulas unidireccionales, proliferan bacterias ácido-lácticas en vez de ácido-acéticas, logrando un control milimétrico de temperatura, pH y presión que antes era imposible en fermentaciones abiertas.',
    impactoEnTaza: 'Perfiles exóticos y complejos: notas a frutas tropicales (maracuyá, mango), especias dulces, canela o yogur frutal.',
    filtroCatalogoQuery: 'proceso=Anaeróbico',
    terminosRelacionados: ['maceracion-carbonica', 'proceso-natural']
  },
  {
    slug: 'maceracion-carbonica',
    termino: 'Maceración Carbónica',
    categoria: 'procesos',
    categoriaNombre: 'Procesos & Fermentación',
    icono: '🍇',
    resumen: 'Técnica heredada de la vinicultura donde se inyecta dióxido de carbono (CO₂) a presión.',
    explicacion: 'Las cerezas enteras se introducen en tanques de acero inoxidable inyectados con CO₂ forzado, desplazando el aire y promoviendo una fermentación intracelular dentro de cada cereza individual antes de que la piel se rompa.',
    impactoEnTaza: 'Sabores brillantes y efervescentes que recuerdan a vino tinto, chicle de frutas, frutos silvestres maduros y licor dulce.',
    filtroCatalogoQuery: 'proceso=Maceración+Carbónica',
    terminosRelacionados: ['fermentacion-anaerobica', 'proceso-natural']
  },
  {
    slug: 'descafeinado-swiss-water',
    termino: 'Descafeinado Swiss Water / Caña',
    categoria: 'procesos',
    categoriaNombre: 'Procesos & Fermentación',
    icono: '🌿',
    resumen: 'Métodos naturales que eliminan la cafeína con agua pura o acetato de caña de azúcar, sin químicos sintéticos.',
    explicacion: 'A diferencia de los procesos industriales con cloruro de metileno, el proceso Swiss Water usa agua y filtros de carbón activado saturados con solubles de café. El proceso Sugar Cane (EA) utiliza acetato de etilo extraído de la fermentación de caña de azúcar colombiana.',
    impactoEnTaza: 'Conserva el 99.9% de los compuestos aromáticos originales con notas dulces a caramelo, panela y chocolate, desmitificando que el descafeinado no tiene sabor.',
    filtroCatalogoQuery: 'q=descafeinado',
    terminosRelacionados: ['proceso-lavado']
  },

  // =========================================================================
  // 2. BOTÁNICA & ORIGEN
  // =========================================================================
  {
    slug: 'arabica-vs-robusta',
    termino: 'Café Arábica vs Robusta',
    categoria: 'botanica',
    categoriaNombre: 'Botánica & Origen',
    icono: '🌱',
    resumen: 'Las dos especies comerciales principales. El café de especialidad utiliza casi exclusivamente Coffea Arabica.',
    explicacion: 'Coffea Arabica (44 cromosomas) crece en alturas elevadas y produce sabores complejos, florales y frutales con menor cafeína (1.2%). Coffea Canephora o Robusta (22 cromosomas) resiste plagas a baja altura, tiene el doble de cafeína y perfil más amargo y terroso.',
    impactoEnTaza: 'El Arábica ofrece notas aromáticas finas, acidez elegante y dulzura natural. El café comercial de supermercado suele ser mezcla con Robusta para abaratar costos.',
    filtroCatalogoQuery: 'category=cafe',
    terminosRelacionados: ['variedad-geisha', 'altura-msnm', 'terroir']
  },
  {
    slug: 'variedad-geisha',
    termino: 'Variedad Geisha (Gesha)',
    categoria: 'botanica',
    categoriaNombre: 'Botánica & Origen',
    icono: '👑',
    resumen: 'La variedad más cotizada del mundo, famosa por su perfil floral etéreo similar al té de jazmín.',
    explicacion: 'Originaria de los bosques de Gesha en Etiopía, fue redescubierta en Panamá en 2004 en la Finca Hacienda La Esmeralda. Sus árboles tienen hojas alargadas y ramas espaciadas que producen bajas cosechas de altísima calidad.',
    impactoEnTaza: 'Inconfundible aroma a flor de jazmín, bergamota, té negro Earl Grey, durazno blanco y miel de azahar. De acidez cristalina y cuerpo sedoso.',
    filtroCatalogoQuery: 'variety=Geisha',
    terminosRelacionados: ['variedad-bourbon-rosado', 'puntaje-sca']
  },
  {
    slug: 'variedad-caturra-castillo',
    termino: 'Variedades Caturra y Castillo',
    categoria: 'botanica',
    categoriaNombre: 'Botánica & Origen',
    icono: '🌿',
    resumen: 'Las columnas vertebrales de la caficultura colombiana y latinoamericana de calidad.',
    explicacion: 'Caturra es una mutación natural enana del Bourbon descubierta en Brasil, de gran dulzura y fácil cosecha. Castillo fue desarrollada por Cenicafé en Colombia cruzando Caturra con el Híbrido de Timor para resistir la roya sin perder calidad de taza.',
    impactoEnTaza: 'Excelente equilibrio con notas clásicas a chocolate con leche, caramelo, manzana roja y nuez tostada.',
    filtroCatalogoQuery: 'country=Colombia',
    terminosRelacionados: ['terroir', 'altura-msnm']
  },
  {
    slug: 'variedad-bourbon-rosado',
    termino: 'Variedad Bourbon Rosado (Pink Bourbon)',
    categoria: 'botanica',
    categoriaNombre: 'Botánica & Origen',
    icono: '🌸',
    resumen: 'Cereza que madura en un tono rosado distintivo en la región del Huila, Colombia.',
    explicacion: 'Estudios genéticos recientes indican que podría ser una variedad landrace etíope domesticada en Colombia más que una simple mutación de Bourbon. Se destaca por una concentración inusualmente alta de glucosa en el fruto.',
    impactoEnTaza: 'Alta complejidad con notas a papaya, jazmín, pomelo rosado, flores blancas y caramelo suave.',
    filtroCatalogoQuery: 'variety=Bourbon+Rosado',
    terminosRelacionados: ['variedad-geisha', 'terroir']
  },
  {
    slug: 'altura-msnm',
    termino: 'Altitud de Cultivo (msnm)',
    categoria: 'botanica',
    categoriaNombre: 'Botánica & Origen',
    icono: '⛰️',
    resumen: 'Metros sobre el nivel del mar donde crecen los cafetos (generalmente 1.200 a 2.200 msnm).',
    explicacion: 'A mayor altitud, las temperaturas nocturnas son más bajas. Esto ralentiza la maduración de la cereza, permitiendo que el grano acumule más densidad celular, azúcares complejos y ácidos orgánicos que los cafés de tierras bajas.',
    impactoEnTaza: 'Granos de gran altitud (+1.600 msnm) se traducen en acidez vibrante, mayor complejidad aromática y notas cítricas y florales refinadas.',
    filtroCatalogoQuery: '',
    terminosRelacionados: ['terroir', 'microlote']
  },
  {
    slug: 'terroir',
    termino: 'Terroir (Terruño)',
    categoria: 'botanica',
    categoriaNombre: 'Botánica & Origen',
    icono: '🌍',
    resumen: 'Conjunto de suelo, microclima, lluvia, radiación solar y entorno biológico de una finca.',
    explicacion: 'Dos cafetos idénticos de la misma variedad sembrados a la misma altitud producirán cafés radicalmente distintos si uno crece en suelo volcánico con sombra de plátano en Guatemala y el otro en tierra arcillosa en Brasil.',
    impactoEnTaza: 'Define la firma geográfica única del café (mineralidad, dulzura básica y tipo predominante de acidez).',
    filtroCatalogoQuery: '',
    terminosRelacionados: ['altura-msnm', 'microlote']
  },
  {
    slug: 'microlote',
    termino: 'Microlote (Micro-lot)',
    categoria: 'botanica',
    categoriaNombre: 'Botánica & Origen',
    icono: '📦',
    resumen: 'Lote exclusivo de café proveniente de una sola parcela o día de cosecha excepcional.',
    explicacion: 'En lugar de mezclar todo el café de la finca, el productor selecciona unas pocas hectáreas o árboles de una variedad específica recolectados en su punto óptimo de grados Brix (madurez de azúcar). Suele producir solo entre 5 y 20 sacos por año.',
    impactoEnTaza: 'Trazabilidad 100% transparente hasta el productor, con puntajes SCA usualmente superiores a 86 puntos y consistencia impecable.',
    filtroCatalogoQuery: '',
    terminosRelacionados: ['puntaje-sca', 'terroir']
  },

  // =========================================================================
  // 3. TUESTE & COLORIMETRÍA
  // =========================================================================
  {
    slug: 'escala-agtron',
    termino: 'Escala Agtron (SCAA)',
    categoria: 'tueste',
    categoriaNombre: 'Tueste & Colorimetría',
    icono: '📊',
    resumen: 'Escala espectrofotométrica de 0 a 100 que mide con precisión el color exacto del café tostado.',
    explicacion: 'A diferencia de los nombres subjetivos ("medio", "oscuro"), un lector Agtron mide la luz infrarroja reflejada por el café molido. Números más altos (Agtron #75-#90) representan tuestes claros; números medios (Agtron #55-#65) tuestes medios; y números bajos (Agtron #25-#40) tuestes oscuros.',
    impactoEnTaza: 'Agtron alto = notas frutales y acidez viva. Agtron bajo = notas a caramelo tostado, cacao amargo y mayor cuerpo pero menor acidez.',
    filtroCatalogoQuery: 'tueste=Medio',
    terminosRelacionados: ['tueste-claro', 'tueste-medio', 'primer-crack']
  },
  {
    slug: 'tueste-claro',
    termino: 'Tueste Claro (Light / Filter Roast)',
    categoria: 'tueste',
    categoriaNombre: 'Tueste & Colorimetría',
    icono: '🟡',
    resumen: 'El café se tuesta el tiempo justo para desarrollar azúcares sin quemar los aceites ni el origen.',
    explicacion: 'Se retira poco después de terminar el primer crack (Agtron #75 a #90). El calor transforma los ácidos clorogénicos sin enmascarar las características botánicas intrínsecas del grano.',
    impactoEnTaza: 'Color ámbar claro en taza, acidez viva, notas florales, cítricas y herbales. Ideal para métodos de filtro como V60, Chemex y Aeropress.',
    filtroCatalogoQuery: 'tueste=Claro',
    terminosRelacionados: ['escala-agtron', 'tueste-medio']
  },
  {
    slug: 'tueste-medio',
    termino: 'Tueste Medio (Omniroast)',
    categoria: 'tueste',
    categoriaNombre: 'Tueste & Colorimetría',
    icono: '🟤',
    resumen: 'El punto de equilibrio perfecto entre acidez frutal y dulzura caramelizada.',
    explicacion: 'Permite que el café funcione de manera versátil tanto en métodos de goteo (V60, cafetera de filtro) como en máquinas de espresso o moka italiana, desarrollando cuerpo sin carbonizar.',
    impactoEnTaza: 'Excelente dulzura a chancaca o toffee, cuerpo redondo y acidez moderada bien balanceada.',
    filtroCatalogoQuery: 'tueste=Medio',
    terminosRelacionados: ['escala-agtron', 'tueste-oscuro']
  },
  {
    slug: 'tueste-oscuro',
    termino: 'Tueste Oscuro (Dark Roast)',
    categoria: 'tueste',
    categoriaNombre: 'Tueste & Colorimetría',
    icono: '⚫',
    resumen: 'Tueste prolongado donde predominan los sabores de pirólisis y caramelización intensa.',
    explicacion: 'Los granos llegan cerca del segundo crack o lo superan (Agtron < #45), provocando que los aceites internos emerjan a la superficie de la semilla. La acidez original del grano desaparece casi por completo.',
    impactoEnTaza: 'Sabores amargos placenteros a chocolate 85%, ceniza noble, nuez tostada y humo. Muy buscado para acompañar con leche o en ristretto tradicional.',
    filtroCatalogoQuery: 'tueste=Oscuro',
    terminosRelacionados: ['tueste-medio', 'escala-agtron']
  },
  {
    slug: 'primer-crack',
    termino: 'Primer Crack (First Crack)',
    categoria: 'tueste',
    categoriaNombre: 'Tueste & Colorimetría',
    icono: '💥',
    resumen: 'Sonido similar a palomitas de maíz que indica que el grano se abrió y comenzó a desarrollar sabor.',
    explicacion: 'Alrededor de los 195°C a 205°C, la presión interna de vapor de agua y gases rompe la estructura celular del grano. Es el hito crítico donde el grano pasa de ser una semilla verde a café bebible.',
    impactoEnTaza: 'El tiempo transcurrido desde el inicio del primer crack hasta descargar el tueste (Rate of Rise / DTR) determina si el café sabrá a pasto verde (subdesarrollado) o dulce y aromático.',
    filtroCatalogoQuery: '',
    terminosRelacionados: ['escala-agtron', 'tueste-claro']
  },
  {
    slug: 'desgasificacion',
    termino: 'Desgasificación & Fecha de Tueste',
    categoria: 'tueste',
    categoriaNombre: 'Tueste & Colorimetría',
    icono: '⏳',
    resumen: 'Tiempo de reposo necesario para que el grano recién tostado libere dióxido de carbono atrapado.',
    explicacion: 'Un café tostado ayer genera tantas burbujas de CO₂ al entrar en contacto con agua caliente que impide una extracción uniforme. El café de especialidad alcanza su punto óptimo de consumo entre 7 y 28 días tras la fecha de tueste.',
    impactoEnTaza: 'Café demasiado fresco = notas ásperas y burbujeo caótico. Café con reposo adecuado = crema sedosa en espresso y taza aromática nítida en filtro.',
    filtroCatalogoQuery: '',
    terminosRelacionados: ['preinfusion-bloom']
  },

  // =========================================================================
  // 4. CATA & ESTÁNDAR SCA
  // =========================================================================
  {
    slug: 'puntaje-sca',
    termino: 'Puntaje SCA (Escala 0 a 100)',
    categoria: 'cata',
    categoriaNombre: 'Cata & Estándar SCA',
    icono: '🏆',
    resumen: 'Calificación oficial otorgada por catadores certificados Q-Grader. Solo los cafés con 80+ puntos son de especialidad.',
    explicacion: 'Evalúa 10 atributos de 0 a 10 puntos: fragancia/aroma, sabor, retrogusto, acidez, cuerpo, balance, uniformidad, taza limpia, dulzura y apreciación global. De 80 a 84.99 es Especialidad Muy Buena; de 85 a 89.99 Excelente; y 90+ puntos es Excepcional (Super Specialty).',
    impactoEnTaza: 'A mayor puntaje SCA, mayor complejidad, ausencia total de defectos primarios (granos negros, vinagres) y mayor claridad de sabor.',
    filtroCatalogoQuery: 'sort_by=kilo',
    terminosRelacionados: ['rueda-sabores-sca', 'notas-de-cata']
  },
  {
    slug: 'rueda-sabores-sca',
    termino: 'Rueda de Sabores SCA',
    categoria: 'cata',
    categoriaNombre: 'Cata & Estándar SCA',
    icono: '🎡',
    resumen: 'El léxico universal desarrollado por World Coffee Research y SCA para describir lo que saboreamos.',
    explicacion: 'Diseñada con rigor científico sensorial, organiza cientos de descriptores desde el centro (familias macro: Frutal, Floral, Dulce, Especiado, etc.) hacia el borde exterior con matices específicos (frambuesa, jazmín, miel, avellana).',
    impactoEnTaza: 'Permite que un tostador en Santiago y un comprador en Tokio hablen exactamente el mismo idioma organoléptico.',
    filtroCatalogoQuery: 'notes=frutos+rojos',
    terminosRelacionados: ['notas-de-cata', 'puntaje-sca']
  },
  {
    slug: 'notas-de-cata',
    termino: 'Notas de Cata (Perfil Sensorial)',
    categoria: 'cata',
    categoriaNombre: 'Cata & Estándar SCA',
    icono: '👃',
    resumen: 'Recuerdos sensoriales naturales que evoca el grano, sin adición de saborizantes artificiales.',
    explicacion: 'El café contiene más de 800 compuestos volátiles aromáticos (más que el vino). Cuando un café dice "notas a durazno y caramelo", no tiene durazno agregado: los ésteres y aldehídos naturales del grano activan los mismos receptores olfativos en nuestro cerebro.',
    impactoEnTaza: 'Guía fundamental para elegir el café que más se adapta a tu gusto personal antes de comprar.',
    filtroCatalogoQuery: 'notes=chocolate',
    terminosRelacionados: ['rueda-sabores-sca', 'puntaje-sca']
  },
  {
    slug: 'acidez-citrica-malica-fosforica',
    termino: 'Acidez Cítrica vs Málica vs Fosfórica',
    categoria: 'cata',
    categoriaNombre: 'Cata & Estándar SCA',
    icono: '🍋',
    resumen: 'La acidez en café de especialidad no es amargura: es el brillo frutal que da vivacidad a la taza.',
    explicacion: 'La acidez cítrica recuerda a limón dulce o naranja (típica en Kenia y Colombia); la acidez málica recuerda a manzana verde crujiente o uva blanca (típica en Etiopía y Centroamérica); y la acidez fosfórica es efervescente como una bebida gaseosa.',
    impactoEnTaza: 'Una acidez balanceada despierta el paladar e incrementa la sensación de dulzura general del café.',
    filtroCatalogoQuery: 'notes=citrico',
    terminosRelacionados: ['cuerpo-sensacion-boca', 'notas-de-cata']
  },
  {
    slug: 'cuerpo-sensacion-boca',
    termino: 'Cuerpo (Sensación en Boca / Mouthfeel)',
    categoria: 'cata',
    categoriaNombre: 'Cata & Estándar SCA',
    icono: '🥛',
    resumen: 'El peso táctil, viscosidad y textura que el café genera en la lengua.',
    explicacion: 'No se refiere al sabor, sino a la física de la bebida. Se describe como acuoso, similar al té, sedoso, cremoso, almibarado o denso como chocolate derretido.',
    impactoEnTaza: 'Los métodos de inmersión (Prensa Francesa) y espresso dan mucho cuerpo; los métodos con filtro de papel grueso (Chemex, V60) dan cuerpo ligero y limpio.',
    filtroCatalogoQuery: '',
    terminosRelacionados: ['retrogusto', 'tds-extraccion']
  },
  {
    slug: 'retrogusto-aftertaste',
    termino: 'Retrogusto (Aftertaste / Final)',
    categoria: 'cata',
    categoriaNombre: 'Cata & Estándar SCA',
    icono: '✨',
    resumen: 'Los aromas y sabores que permanecen en tu garganta y paladar tras tragar el café.',
    explicacion: 'En café de mala calidad, el final es seco, astringente o recuerda a ceniza. En café de especialidad, los azúcares y aceites dejan una estela agradable y prolongada durante minutos.',
    impactoEnTaza: 'Un retrogusto largo a cacao dulce, flores o frutos secos es uno de los mejores indicadores de alta puntuación en cata.',
    filtroCatalogoQuery: '',
    terminosRelacionados: ['puntaje-sca', 'notas-de-cata']
  },

  // =========================================================================
  // 5. PREPARACIÓN & EXTRACCIÓN
  // =========================================================================
  {
    slug: 'ratio-extraccion',
    termino: 'Ratio de Preparación (Brew Ratio)',
    categoria: 'extraccion',
    categoriaNombre: 'Preparación & Extracción',
    icono: '⚖️',
    resumen: 'La proporción exacta en gramos entre café molido y agua caliente (ej. 1:16).',
    explicacion: 'Un ratio 1:16 significa que por cada gramo de café seco usarás 16 gramos (o mililitros) de agua. Para una taza estándar con 15g de café molido, se vierten 240g de agua total (15 × 16 = 240).',
    impactoEnTaza: 'Ratios más cortos (1:13 a 1:14) dan bebidas intensas y densas; ratios más largos (1:16 a 1:18) permiten separar notas florales sutiles y mayor claridad.',
    filtroCatalogoQuery: '',
    terminosRelacionados: ['tds-extraccion', 'preinfusion-bloom']
  },
  {
    slug: 'preinfusion-bloom',
    termino: 'Preinfusión (Bloom / Florecimiento)',
    categoria: 'extraccion',
    categoriaNombre: 'Preparación & Extracción',
    icono: '🫧',
    resumen: 'El primer vertido de agua (el doble del peso del café) durante 30 a 45 segundos.',
    explicacion: 'Permite que el café recién molido libere el dióxido de carbono atrapado en forma de burbujas antes de iniciar la extracción principal. Si se extrae de inmediato sin bloom, el gas repele el agua impidiendo extraer los azúcares.',
    impactoEnTaza: 'Garantiza una extracción uniforme, evitando que el agua busque canales fáciles y dejando la taza dulce y equilibrada.',
    filtroCatalogoQuery: '',
    terminosRelacionados: ['canalizacion-channelling', 'desgasificacion']
  },
  {
    slug: 'canalizacion-channelling',
    termino: 'Canalización (Channelling)',
    categoria: 'extraccion',
    categoriaNombre: 'Preparación & Extracción',
    icono: '⚡',
    resumen: 'Defecto donde el agua encuentra grietas o caminos de menor resistencia en la pastilla de café.',
    explicacion: 'El agua siempre buscará el camino más fácil. Cuando se canaliza, extrae en exceso los granos cercanos a la grieta (sabor amargo y astringente) y deja los demás secos (sabor agrio y subextraído).',
    impactoEnTaza: 'Taza incoherente que sabe amarga y agria al mismo tiempo, con aspereza en la garganta. Se previene distribuyendo el café de forma pareja y compactando recto.',
    filtroCatalogoQuery: '',
    terminosRelacionados: ['preinfusion-bloom', 'ratio-extraccion']
  },
  {
    slug: 'tds-extraccion',
    termino: 'TDS (Sólidos Disueltos Totales) & Rendimiento',
    categoria: 'extraccion',
    categoriaNombre: 'Preparación & Extracción',
    icono: '🔬',
    resumen: 'Medición refractométrica del porcentaje de masa de café disuelta en el agua.',
    explicacion: 'Una taza de café de filtro está compuesta por ~98.5% de agua y ~1.5% de sólidos de café disueltos (TDS = 1.25% - 1.50%). El rendimiento de extracción ideal según la SCA se sitúa entre el 18% y el 22% del peso del grano seco.',
    impactoEnTaza: 'Menos del 18% = Subextraído (ácido, pastoso, salado). Más del 22% = Sobreextraído (amargo, seco, amaderado). Entre 18% y 22% = Zona dorada de dulzura máxima.',
    filtroCatalogoQuery: '',
    terminosRelacionados: ['ratio-extraccion', 'cuerpo-sensacion-boca']
  }
];

export function searchGlossaryTerms(query: string = '', category: string = ''): GlossaryTerm[] {
  const cleanQ = query.trim().toLowerCase();
  const cleanCat = category.trim().toLowerCase();

  return GLOSSARY_TERMS.filter(term => {
    const matchesCategory = !cleanCat || term.categoria.toLowerCase() === cleanCat;
    if (!matchesCategory) return false;

    if (!cleanQ) return true;

    return (
      term.termino.toLowerCase().includes(cleanQ) ||
      term.resumen.toLowerCase().includes(cleanQ) ||
      term.explicacion.toLowerCase().includes(cleanQ) ||
      term.impactoEnTaza.toLowerCase().includes(cleanQ) ||
      term.categoriaNombre.toLowerCase().includes(cleanQ)
    );
  });
}
