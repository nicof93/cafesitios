import { e as createComponent, m as maybeRenderHead, g as addAttribute, r as renderTemplate, l as renderScript, h as createAstro, n as defineScriptVars, k as renderComponent } from '../../chunks/astro/server_D990-clo.mjs';
import 'piccolore';
import { $ as $$BaseLayout } from '../../chunks/BaseLayout_BWXSiVi2.mjs';
import 'clsx';
import { C as CoffeeProduct } from '../../chunks/CoffeeProduct_Btm9wch6.mjs';
import { H as HttpClient } from '../../chunks/HttpClient_Dd_rjSA5.mjs';
export { renderers } from '../../renderers.mjs';

const SCA_FLAVOR_WHEEL_DATA = [
  {
    id: "floral",
    nombre: "Floral",
    color: "#8B5CF6",
    colorFondo: "#F5F3FF",
    colorBorde: "#DDD6FE",
    colorTexto: "#6D28D9",
    icono: "🌸",
    notas: [
      "Floral",
      "Jazmín",
      "Flor blanca",
      "Azahar",
      "Rosa",
      "Lavanda",
      "Manzanilla",
      "Hibisco",
      "Té negro",
      "Té verde",
      "Bergamota",
      "Magnolia"
    ]
  },
  {
    id: "citrico",
    nombre: "Frutal / Cítrico",
    color: "#F59E0B",
    colorFondo: "#FFFBEB",
    colorBorde: "#FDE68A",
    colorTexto: "#B45309",
    icono: "🍋",
    notas: [
      "Cítrico",
      "Limón",
      "Lima",
      "Naranja",
      "Mandarina",
      "Pomelo",
      "Clementina",
      "Manzana verde",
      "Cidra",
      "Hierba luisa"
    ]
  },
  {
    id: "frutos_rojos",
    nombre: "Frutal / Frutos Rojos",
    color: "#E11D48",
    colorFondo: "#FFF1F2",
    colorBorde: "#FECDD3",
    colorTexto: "#BE123C",
    icono: "🍓",
    notas: [
      "Frutos rojos",
      "Frutilla",
      "Frambuesa",
      "Arándano",
      "Cereza",
      "Mora",
      "Grosella",
      "Ciruela",
      "Granada",
      "Casis",
      "Uva",
      "Vino"
    ]
  },
  {
    id: "dulce_chocolate",
    nombre: "Dulce / Chocolate",
    color: "#B45309",
    colorFondo: "#FEF3C7",
    colorBorde: "#FDE68A",
    colorTexto: "#92400E",
    icono: "🍫",
    notas: [
      "Caramelo",
      "Chocolate",
      "Cacao",
      "Panela",
      "Miel",
      "Vainilla",
      "Chocolate amargo",
      "Chocolate con leche",
      "Toffee",
      "Dulce de leche",
      "Azúcar morena",
      "Melaza",
      "Butterscotch",
      "Praliné"
    ]
  },
  {
    id: "frutos_secos",
    nombre: "Frutos Secos",
    color: "#059669",
    colorFondo: "#ECFDF5",
    colorBorde: "#A7F3D0",
    colorTexto: "#047857",
    icono: "🥜",
    notas: [
      "Frutos secos",
      "Almendra",
      "Nuez",
      "Avellana",
      "Maní",
      "Castaña",
      "Pistacho",
      "Pecana",
      "Nuez de macadamia"
    ]
  }
];
function sanitizeNote(str) {
  if (!str) return "";
  return str.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "").trim();
}
function matchProductNotesToWheel(productNotes) {
  const sanitizedProductNotes = productNotes.map((n) => sanitizeNote(n));
  const unmatchedSet = new Set(productNotes);
  const wheelFamilies = SCA_FLAVOR_WHEEL_DATA.map((family) => {
    let activeNotesCount = 0;
    const notes = family.notas.map((canonical) => {
      const sanitizedCanon = sanitizeNote(canonical);
      const matched = sanitizedProductNotes.some((pn) => {
        if (!pn) return false;
        return pn === sanitizedCanon || pn.includes(sanitizedCanon) || sanitizedCanon.includes(pn);
      });
      if (matched) {
        activeNotesCount++;
        productNotes.forEach((orig) => {
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
  const activeFamilies = wheelFamilies.filter((wf) => wf.activeNotesCount > 0).map((wf) => wf.family);
  return {
    wheelFamilies,
    activeFamilies,
    unmatchedNotes: Array.from(unmatchedSet)
  };
}

const $$Astro$1 = createAstro();
const $$FlavorWheel = createComponent(($$result, $$props, $$slots) => {
  const Astro2 = $$result.createAstro($$Astro$1, $$props, $$slots);
  Astro2.self = $$FlavorWheel;
  const { product } = Astro2.props;
  const productNotes = (product.notas_cata || []).map((n) => {
    if (typeof n === "string") return n.trim();
    if (n && typeof n === "object") {
      return String(n.nombre || n.clave_normalizada || "").trim();
    }
    return String(n).trim();
  }).filter(Boolean);
  const { wheelFamilies, unmatchedNotes } = matchProductNotesToWheel(productNotes);
  const notesText = productNotes.join(" ").toLowerCase();
  const processText = (product.proceso || "").toLowerCase();
  const roastText = (product.tueste || "").toLowerCase();
  let dulzura = 6;
  let acidez = 6;
  let frutosRojos = 5;
  let floral = 5;
  let cuerpo = 6;
  let frutosSecos = 5;
  if (processText.includes("lavado") || processText.includes("washed")) {
    acidez += 2;
    floral += 1;
    cuerpo -= 1;
  } else if (processText.includes("natural")) {
    frutosRojos += 3;
    dulzura += 2;
    cuerpo += 1;
    acidez -= 1;
  } else if (processText.includes("honey")) {
    dulzura += 3;
    frutosRojos += 1;
    cuerpo += 1;
  } else if (processText.includes("anaerob") || processText.includes("maceracion")) {
    dulzura += 3;
    frutosRojos += 3;
    cuerpo += 2;
  }
  if (roastText.includes("claro") || roastText.includes("light")) {
    acidez += 2;
    floral += 2;
    cuerpo -= 1;
  } else if (roastText.includes("oscuro") || roastText.includes("dark")) {
    cuerpo += 3;
    frutosSecos += 2;
    acidez -= 2;
  }
  if (/(caramel|panela|miel|toffee|vainill|dulce|chancaca|azucar)/i.test(notesText)) dulzura += 2;
  if (/(limon|citric|naranja|pomelo|manzana|acidez|lima|bergamota)/i.test(notesText)) acidez += 3;
  if (/(frutilla|fresa|frambuesa|mora|arandano|cereza|berry|berries|uva|ciruela)/i.test(notesText)) frutosRojos += 3;
  if (/(jazmin|floral|flores|azahar|te negro|rosa|lavanda)/i.test(notesText)) floral += 3;
  if (/(almendra|nuez|avellana|mani|cacao|chocolate|castana)/i.test(notesText)) {
    frutosSecos += 2;
    cuerpo += 1;
  }
  const clamp = (val) => Math.min(10, Math.max(2, val));
  const scores = {
    dulzura: clamp(dulzura),
    acidez: clamp(acidez),
    frutosRojos: clamp(frutosRojos),
    floral: clamp(floral),
    cuerpo: clamp(cuerpo),
    frutosSecos: clamp(frutosSecos)
  };
  const polarCenter = 160;
  const polarMaxRadius = 120;
  const polarAxes = [
    { name: "Dulzura", value: scores.dulzura, angle: -90, color: "#F59E0B" },
    { name: "Acidez", value: scores.acidez, angle: -30, color: "#EAB308" },
    { name: "Frutos Rojos", value: scores.frutosRojos, angle: 30, color: "#E11D48" },
    { name: "Floral", value: scores.floral, angle: 90, color: "#8B5CF6" },
    { name: "Cuerpo", value: scores.cuerpo, angle: 150, color: "#78350F" },
    { name: "Frutos Secos", value: scores.frutosSecos, angle: 210, color: "#059669" }
  ];
  function getPolarCoord(angleDeg, val) {
    const rad = angleDeg * Math.PI / 180;
    const r = val / 10 * polarMaxRadius;
    return {
      x: polarCenter + r * Math.cos(rad),
      y: polarCenter + r * Math.sin(rad)
    };
  }
  const polarPolygonPoints = polarAxes.map((axis) => {
    const pt = getPolarCoord(axis.angle, axis.value);
    return `${pt.x.toFixed(1)},${pt.y.toFixed(1)}`;
  }).join(" ");
  let metodoSugerido = "Vers\xE1til (Filtro o Espresso)";
  let metodoIcono = "\u2615";
  let caracteristicaPrincipal = "Equilibrado y balanceado";
  if (scores.acidez >= 8 || scores.floral >= 8) {
    metodoSugerido = "Filtrados manuales (V60, Chemex, Origami o Aeropress)";
    metodoIcono = "\u{1F9EA}";
    caracteristicaPrincipal = "Perfil brillante, floral y arom\xE1tico";
  } else if (scores.cuerpo >= 8 || scores.dulzura >= 8) {
    metodoSugerido = "Espresso, Moka Italiana o Prensa Francesa";
    metodoIcono = "\u26A1";
    caracteristicaPrincipal = "Perfil dulce, achocolatado y con gran cuerpo";
  }
  return renderTemplate`${maybeRenderHead()}<section class="bg-white p-6 sm:p-8 rounded-3xl border border-stone-200/80 shadow-2xs space-y-8" id="sensory-profile-section"> <!-- CABECERA SENSORIAL CON TABS --> <div class="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-stone-100 pb-5"> <div class="space-y-1"> <div class="flex items-center gap-2"> <span class="text-xs font-bold uppercase tracking-wider text-emerald-800 bg-emerald-50 px-2.5 py-0.5 rounded-full border border-emerald-100">
Laboratorio Sensorial SCA
</span> <span class="text-xs text-stone-400">
• ${productNotes.length} notas analizadas
</span> </div> <h2 class="text-lg sm:text-xl font-extrabold text-stone-900 tracking-tight flex items-center gap-2"> <span>🧭</span> Rueda de Sabores y Perfil de Coordenadas Polares
</h2> <p class="text-xs text-stone-500 max-w-2xl">
Visualiza el perfil organoléptico homologado según la Rueda de Sabores de la Specialty Coffee Association (SCA). Las notas y familias activas en este café se resaltan en colores vivos.
</p> </div> <!-- BOTONES SELECTORES DE VISTA (RUEDA SCA vs COORDENADAS POLARES) --> <div class="inline-flex rounded-2xl border border-stone-200 bg-stone-100/80 p-1 text-xs font-semibold self-start md:self-auto"> <button id="btn-view-polar" type="button" class="flex items-center gap-1.5 rounded-xl bg-white shadow-2xs px-3.5 py-2 text-emerald-800 font-bold transition"> <span>🕸️</span> Coordenadas Polares (Radar)
</button> <button id="btn-view-wheel" type="button" class="flex items-center gap-1.5 rounded-xl px-3.5 py-2 text-stone-500 hover:text-stone-800 transition font-medium"> <span>🎡</span> Rueda de Sabores SCA
</button> </div> </div> <!-- VISTA 1: RUEDA DE SABORES DE ESPECIALIDAD (SCA FLAVOR WHEEL) --> <div id="view-flavor-wheel" class="space-y-8 hidden"> <!-- RESUMEN DE MACRO-FAMILIAS ACTIVAS --> <div class="flex flex-wrap items-center gap-2.5"> <span class="text-xs font-bold text-stone-400 uppercase tracking-wider mr-1">Familias activas:</span> ${wheelFamilies.map((wf) => {
    const isActive = wf.activeNotesCount > 0;
    return renderTemplate`<span${addAttribute(`inline-flex items-center gap-1.5 text-xs font-bold px-3 py-1 rounded-full border transition-all ${isActive ? "shadow-xs scale-105" : "opacity-40 grayscale-[40%]"}`, "class")}${addAttribute({
      backgroundColor: isActive ? wf.family.colorFondo : "#F5F5F4",
      borderColor: isActive ? wf.family.color : "#E7E5E4",
      color: isActive ? wf.family.colorTexto : "#78716C"
    }, "style")}> <span>${wf.family.icono}</span> <span>${wf.family.nombre}</span> <span class="ml-0.5 rounded-full px-1.5 py-0.2 text-[10px]"${addAttribute({
      backgroundColor: isActive ? wf.family.color : "#D6D3D1",
      color: "#FFFFFF"
    }, "style")}> ${wf.activeNotesCount} </span> </span>`;
  })} </div> <!-- RUEDA CIRCULAR VISUAL DE SABORES (GRID DE 5 MACRO-FAMILIAS CON NOTAS RESALTADAS) --> <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4"> ${wheelFamilies.map((wf) => {
    const isActive = wf.activeNotesCount > 0;
    return renderTemplate`<div${addAttribute(`flex flex-col justify-between rounded-2xl p-4 border transition-all duration-200 ${isActive ? "bg-white shadow-sm ring-2" : "bg-stone-50/60 border-stone-200/60 opacity-60"}`, "class")}${addAttribute({
      borderColor: isActive ? wf.family.color : void 0,
      ringColor: isActive ? `${wf.family.color}33` : void 0
    }, "style")}> <!-- CABECERA DE FAMILIA --> <div class="border-b pb-3 mb-3"${addAttribute({ borderColor: `${wf.family.color}25` }, "style")}> <div class="flex items-center justify-between"> <span class="text-xl">${wf.family.icono}</span> ${isActive && renderTemplate`<span class="text-[10px] font-extrabold uppercase px-2 py-0.5 rounded-full"${addAttribute({
      backgroundColor: wf.family.color,
      color: "#FFFFFF"
    }, "style")}> ${wf.activeNotesCount} ${wf.activeNotesCount === 1 ? "nota" : "notas"} </span>`} </div> <h3 class="font-extrabold text-sm mt-1.5"${addAttribute({ color: isActive ? wf.family.colorTexto : "#44403C" }, "style")}> ${wf.family.nombre} </h3> </div> <!-- LISTA DE DESCRIPTORES CANÓNICOS DE LA FAMILIA --> <div class="flex flex-wrap gap-1.5 content-start flex-1"> ${wf.notes.map((note) => renderTemplate`<span${addAttribute(`text-[11px] font-semibold px-2 py-1 rounded-lg border transition-all inline-flex items-center gap-1 ${note.isActive ? "shadow-xs font-bold" : "border-transparent text-stone-400 bg-stone-100/80 hover:bg-stone-200/50"}`, "class")}${addAttribute(note.isActive ? {
      backgroundColor: wf.family.colorFondo,
      borderColor: wf.family.color,
      color: wf.family.colorTexto
    } : {}, "style")}${addAttribute(note.isActive ? `Nota detectada en ${product.nombre}` : `Descriptor can\xF3nico de ${wf.family.nombre}`, "title")}> ${note.isActive && renderTemplate`<span class="text-[9px]">★</span>`} <span>${note.name}</span> </span>`)} </div>  ${isActive && renderTemplate`<div class="mt-3 pt-2 text-[10px] font-bold text-right"${addAttribute({ color: wf.family.colorTexto }, "style")}>
✓ Presente en taza
</div>`} </div>`;
  })} </div> <!-- NOTAS ESPECÍFICAS DETECTADAS FUERA DEL MAPA ESTRICTO (SI HUBIESE) --> ${unmatchedNotes.length > 0 && renderTemplate`<div class="bg-amber-50/60 p-4 rounded-2xl border border-amber-200/70 space-y-1"> <span class="text-[10px] uppercase font-bold tracking-wider text-amber-800">
Otros descriptores reportados por el tostador:
</span> <div class="flex flex-wrap gap-1.5 pt-1"> ${unmatchedNotes.map((n) => renderTemplate`<span class="text-xs bg-white text-stone-700 font-medium px-2.5 py-1 rounded-lg border border-amber-200 shadow-2xs">
☕ ${n} </span>`)} </div> </div>`} </div> <!-- VISTA 2: GRÁFICO DE COORDENADAS POLARES (RADAR SENSORIAL 6 EJES) --> <div id="view-polar-chart" class="block space-y-8"> <div class="grid grid-cols-1 lg:grid-cols-12 gap-8 items-center"> <!-- COLUMNA 1: GRÁFICO RADIAL VECTORIAL SVG NATIVO (100% FIABLE, SIN RETRASO) --> <div class="lg:col-span-6 flex flex-col items-center justify-center bg-stone-50/50 rounded-2xl p-4 sm:p-6 border border-stone-100"> <div class="relative w-full max-w-[340px] aspect-square"> <svg viewBox="0 0 320 320" class="w-full h-full drop-shadow-sm select-none" role="img" aria-label="Gráfico de coordenadas polares para perfil de café"> <!-- Círculos concéntricos de referencia (Escala 2, 4, 6, 8, 10) --> ${[2, 4, 6, 8, 10].map((level) => {
    const r = level / 10 * polarMaxRadius;
    return renderTemplate`<circle${addAttribute(polarCenter, "cx")}${addAttribute(polarCenter, "cy")}${addAttribute(r, "r")} fill="none"${addAttribute(level === 10 ? "#D6D3D1" : "#E7E5E4", "stroke")}${addAttribute(level === 10 ? "none" : "3 3", "stroke-dasharray")}${addAttribute(level === 10 ? "1.5" : "1", "stroke-width")}></circle>`;
  })} <!-- Ejes radiales desde el centro a cada dimensión --> ${polarAxes.map((axis) => {
    const edge = getPolarCoord(axis.angle, 10);
    return renderTemplate`<line${addAttribute(polarCenter, "x1")}${addAttribute(polarCenter, "y1")}${addAttribute(edge.x, "x2")}${addAttribute(edge.y, "y2")} stroke="#E7E5E4" stroke-width="1.2"></line>`;
  })} <!-- Polígono relleno de coordenadas del café --> <polygon${addAttribute(polarPolygonPoints, "points")} fill="rgba(16, 185, 129, 0.25)" stroke="#047857" stroke-width="2.5" stroke-linejoin="round"></polygon> <!-- Puntos destacados en cada vértice --> ${polarAxes.map((axis) => {
    const pt = getPolarCoord(axis.angle, axis.value);
    return renderTemplate`<g> <circle${addAttribute(pt.x, "cx")}${addAttribute(pt.y, "cy")} r="5"${addAttribute(axis.color, "fill")} stroke="#FFFFFF" stroke-width="2" class="drop-shadow-xs"></circle> <text${addAttribute(pt.x, "x")}${addAttribute(pt.y - 8, "y")} text-anchor="middle" font-size="10" font-weight="bold" fill="#1C1917"> ${axis.value} </text> </g>`;
  })} <!-- Etiquetas de los 6 Ejes --> ${polarAxes.map((axis) => {
    const labelPos = getPolarCoord(axis.angle, 12.2);
    return renderTemplate`<text${addAttribute(labelPos.x, "x")}${addAttribute(labelPos.y + 4, "y")} text-anchor="middle" font-size="11" font-weight="bold" fill="#44403C"> ${axis.name} </text>`;
  })} </svg> </div> <p class="text-[11px] text-stone-400 mt-2">
Coordenadas normalizadas de 1 (suave) a 10 (intenso)
</p> </div> <!-- COLUMNA 2: INTENSIDADES NUMÉRICAS Y RECOMENDACIÓN --> <div class="lg:col-span-6 space-y-4"> <!-- RECOMENDACIÓN DE MÉTODO --> <div class="bg-gradient-to-br from-emerald-50/70 to-stone-50 p-5 rounded-2xl border border-emerald-200/60 space-y-2"> <div class="flex items-center gap-2.5"> <span class="text-2xl">${metodoIcono}</span> <div> <span class="block text-[10px] uppercase font-bold text-stone-400 tracking-wider">Método de Extracción Recomendado</span> <h3 class="text-sm font-bold text-stone-900">${metodoSugerido}</h3> </div> </div> <p class="text-xs text-stone-600 leading-relaxed font-normal"> ${caracteristicaPrincipal}. Diseñado para extraer el máximo potencial organoléptico de este perfil.
</p> </div> <!-- LISTADO DE INTENSIDADES POR EJE --> <div class="space-y-2"> <span class="block text-[11px] font-bold uppercase tracking-wider text-stone-400">
Intensidad de Atributos Organolépticos
</span> <div class="grid grid-cols-2 gap-2 text-xs"> ${polarAxes.map((axis) => renderTemplate`<div class="flex items-center justify-between p-2.5 rounded-xl bg-stone-50 border border-stone-100"> <span class="flex items-center gap-2 font-medium text-stone-700"> <span class="h-2.5 w-2.5 rounded-full"${addAttribute({ backgroundColor: axis.color }, "style")}></span> <span>${axis.name}</span> </span> <span class="font-extrabold text-stone-900"> ${axis.value} <span class="text-[10px] text-stone-400 font-normal">/10</span> </span> </div>`)} </div> </div> </div> </div> </div> <!-- PIE INFORMATIVO SCA --> <div class="flex flex-col sm:flex-row items-center justify-between gap-3 pt-3 border-t border-stone-100 text-[11px] text-stone-400"> <div class="flex items-center gap-2"> <span>📖</span> <span>Basado en el estándar de cata de la <strong>Specialty Coffee Association (SCA)</strong> y World Coffee Research.</span> </div> <div class="flex items-center gap-3 font-semibold text-emerald-800"> <span>Variedad: ${product.variedad || "Ar\xE1bica"}</span> <span>•</span> <span>Proceso: ${product.proceso || "Tradicional"}</span> </div> </div> </section> ${renderScript($$result, "C:/Users/niko_/OneDrive/Desktop/cafe-sitios/astro-frontend/src/components/product/FlavorWheel.astro?astro&type=script&index=0&lang.ts")}`;
}, "C:/Users/niko_/OneDrive/Desktop/cafe-sitios/astro-frontend/src/components/product/FlavorWheel.astro", void 0);

class GetProductDetailUseCase {
  constructor(http = new HttpClient()) {
    this.http = http;
  }
  async execute(productId) {
    const productData = await this.http.get(`/api/v1/products/${productId}/detail`);
    const product = new CoffeeProduct(productData);
    let matches = [];
    try {
      const matchesData = await this.http.get(`/api/v1/products/${productId}/matches`);
      matches = (matchesData.coincidencias || []).map((m) => new CoffeeProduct(m));
    } catch {
    }
    return { product, matches };
  }
}

var __freeze = Object.freeze;
var __defProp = Object.defineProperty;
var __template = (cooked, raw) => __freeze(__defProp(cooked, "raw", { value: __freeze(cooked.slice()) }));
var _a;
const $$Astro = createAstro();
const $$id = createComponent(async ($$result, $$props, $$slots) => {
  const Astro2 = $$result.createAstro($$Astro, $$props, $$slots);
  Astro2.self = $$id;
  const { id } = Astro2.params;
  if (!id) {
    return Astro2.redirect("/");
  }
  const detailUseCase = new GetProductDetailUseCase();
  let product = null;
  let matches = [];
  try {
    const result = await detailUseCase.execute(id);
    product = result.product;
    matches = result.matches;
  } catch (error) {
    console.error(`Error cargando producto ${id}:`, error);
  }
  if (!product) {
    return Astro2.redirect("/404");
  }
  const bestVariant = product.getBestVariant(true) || product.getBestVariant(false);
  const variantsJson = JSON.stringify(product.variantes);
  const currentPrice = bestVariant?.precio_clp || 0;
  const currentPriceKilo = bestVariant?.precio_por_kilo || 0;
  const historicalPrices = bestVariant?.historial_precios?.map((h) => h.precio_clp) || [currentPrice];
  const minHistorical = historicalPrices.length > 0 ? Math.min(...historicalPrices) : currentPrice;
  const avgHistorical = historicalPrices.length > 0 ? Math.round(historicalPrices.reduce((a, b) => a + b, 0) / historicalPrices.length) : currentPrice;
  const groupedVariantsMap = /* @__PURE__ */ new Map();
  product.variantes.forEach((v) => {
    const key = `${v.formato_gramos}_${v.precio_clp}`;
    if (!groupedVariantsMap.has(key)) {
      groupedVariantsMap.set(key, {
        formato_gramos: v.formato_gramos,
        precio_clp: v.precio_clp,
        precio_original_clp: v.precio_original_clp,
        precio_por_kilo: v.precio_por_kilo,
        en_oferta: v.en_oferta,
        es_estimado: v.es_estimado,
        disponible: v.disponible,
        presentaciones: [v.opcion]
      });
    } else {
      const existing = groupedVariantsMap.get(key);
      if (v.opcion && !existing.presentaciones.includes(v.opcion)) {
        existing.presentaciones.push(v.opcion);
      }
      if (v.disponible) existing.disponible = true;
    }
  });
  const groupedVariants = Array.from(groupedVariantsMap.values()).sort((a, b) => a.precio_por_kilo - b.precio_por_kilo);
  return renderTemplate(_a || (_a = __template(["", " <script>(function(){", "\n  // Guardar en Vistos Recientemente (CU-10)\n  try {\n    const raw = localStorage.getItem('cafesitios_vistos_recientemente_v1');\n    const list = raw ? JSON.parse(raw) : [];\n    const filtered = list.filter(item => item.id !== product.id);\n    filtered.unshift({\n      id: product.id,\n      nombre: product.nombre,\n      tienda: product.tienda,\n      precio: product.variantes?.[0]?.precio_clp || 0,\n      imagen: product.imagen\n    });\n    localStorage.setItem('cafesitios_vistos_recientemente_v1', JSON.stringify(filtered.slice(0, 5)));\n  } catch (e) {\n    console.error('Error registrando visto recientemente:', e);\n  }\n})();<\/script> ", ""])), renderComponent($$result, "BaseLayout", $$BaseLayout, { "title": `${product.nombre} - ${product.tienda} | Comparador Cafesitios`, "description": `Ficha t\xE9cnica y comparativa de precios para ${product.nombre} en ${product.tienda}. ${product.origen ? `Origen: ${product.origen}. ` : ""}Precio por kilo: $${currentPriceKilo.toLocaleString("es-CL")}/kg.`, "ogImage": product.imagen }, { "default": async ($$result2) => renderTemplate` ${maybeRenderHead()}<div class="space-y-10 pb-24"> <!-- BREADCRUMB / RETORNO RÁPIDO --> <nav class="flex items-center gap-2 text-xs text-stone-500" aria-label="Ruta de navegación"> <a href="/" class="hover:text-emerald-800 transition flex items-center gap-1"> <span>←</span> <span>Volver al Catálogo</span> </a> <span class="text-stone-300">/</span> <span class="text-stone-400 font-medium">${product.tienda}</span> <span class="text-stone-300">/</span> <span class="font-semibold text-stone-800 truncate max-w-sm">${product.nombre}</span> </nav> <!-- HERO DE PRODUCTO EN DOS COLUMNAS --> <section class="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start bg-white p-6 sm:p-8 rounded-3xl border border-stone-200/80 shadow-2xs"> <!-- COLUMNA IZQUIERDA: MARCO DE IMAGEN DESTACADO --> <div class="lg:col-span-5 relative flex items-center justify-center bg-[#F4F3ED] rounded-2xl p-6 sm:p-10 border border-stone-100 min-h-[380px] group overflow-hidden"> <img${addAttribute(product.imagen, "src")}${addAttribute(product.nombre, "alt")} referrerpolicy="no-referrer" onerror="this.onerror=null; this.src='https://images.unsplash.com/photo-1559056199-641a0ac8b55e?q=80&w=400&auto=format&fit=crop';" class="max-h-[340px] w-auto object-contain drop-shadow-md transition-transform duration-300 group-hover:scale-105"> <!-- PILL TIENDA Y BADGES SUPERIORES --> <span class="absolute top-4 left-4 bg-white/95 backdrop-blur-xs text-stone-800 text-xs font-bold px-3 py-1 rounded-full shadow-2xs border border-stone-200/60"> ${product.tienda} </span> ${product.puntuacion_sca && renderTemplate`<span class="absolute top-4 right-4 bg-amber-500/90 text-white text-xs font-bold px-2.5 py-1 rounded-full shadow-2xs">
★ ${product.puntuacion_sca} SCA
</span>`} </div> <!-- COLUMNA DERECHA: PANEL DE ESPECIFICACIONES Y CONVERSIÓN --> <div class="lg:col-span-7 flex flex-col justify-between space-y-6"> <div class="space-y-4"> <!-- BADGES SUPERIORES --> <div class="flex flex-wrap items-center gap-2"> <span class="text-xs font-bold text-emerald-800 bg-emerald-50 border border-emerald-200 px-3 py-0.5 rounded-full"> ${product.tienda} </span> ${bestVariant?.es_estimado && renderTemplate`<span class="text-xs font-semibold text-amber-800 bg-amber-50 border border-amber-200 px-2.5 py-0.5 rounded-full" title="Gramaje estimado por fallback de 250g (RN-02)">
⚠️ Gramaje Estimado (250g)
</span>`} </div> <!-- TÍTULO PRINCIPAL --> <h1 class="text-2xl sm:text-3xl font-extrabold text-stone-900 leading-tight tracking-tight"> ${product.nombre} </h1> <!-- PUNTUACIÓN SCA DESTACADA MUY VISTOSA (CALIFICACIÓN Q-GRADER OFICIAL) --> ${product.puntuacion_sca && renderTemplate`<div class="flex items-center gap-3.5 p-4 rounded-2xl bg-gradient-to-r from-amber-500/15 via-amber-400/10 to-amber-50 border-2 border-amber-400/90 shadow-xs"> <div class="flex items-center justify-center w-12 h-12 rounded-2xl bg-gradient-to-br from-amber-500 to-amber-600 text-white font-extrabold text-xl shadow-sm">
★
</div> <div class="space-y-0.5"> <div class="flex items-center gap-2"> <span class="text-xs font-extrabold uppercase tracking-wider text-amber-950">
Puntuación Oficial de Catación:
</span> <span class="text-base sm:text-lg font-black text-amber-950 bg-amber-200/90 border border-amber-300 px-2.5 py-0.5 rounded-xl shadow-2xs"> ${product.puntuacion_sca} SCA
</span> </div> <p class="text-xs font-semibold text-amber-900/90"> ${product.puntuacion_sca >= 90 ? "\u{1F3C6} Calidad Excepcional / Super Specialty (Gourmet Exclusivo)" : product.puntuacion_sca >= 85 ? "\u2728 Calidad Excelente (Especialidad Alta)" : "\u2615 Caf\xE9 de Especialidad Calificado por Catador Q-Grader"} </p> </div> </div>`} <!-- NOTAS DE CATA EN TONOS CÁLIDOS/ÁMBAR --> ${product.notas_cata && product.notas_cata.length > 0 && renderTemplate`<div class="space-y-1.5 pt-1"> <span class="block text-[11px] font-bold uppercase tracking-wider text-stone-400">
Perfil Sensorial & Notas de Cata
</span> <div class="flex flex-wrap gap-1.5"> ${product.notas_cata.map((nota) => {
    const label = typeof nota === "object" && nota !== null ? nota.nombre || nota.clave_normalizada || "" : String(nota);
    return renderTemplate`<span class="inline-flex items-center gap-1 rounded-full bg-amber-50 border border-amber-200/80 text-amber-900 px-3 py-1 text-xs font-semibold shadow-2xs"> <span>☕</span> <span>${label}</span> </span>`;
  })} </div> </div>`} <!-- GRILLA ESTRUCTURADA DE ESPECIFICACIONES TÉCNICAS (CON TONO SUAVE PARA VALORES NO IDENTIFICADOS) --> <div class="pt-2"> <span class="block text-[11px] font-bold uppercase tracking-wider text-stone-400 mb-2">
Ficha Técnica de Origen
</span> <div class="grid grid-cols-2 gap-2.5 text-xs"> <!-- PAÍS / ORIGEN --> <div${addAttribute(`flex items-center gap-2.5 p-3 rounded-xl border transition-all ${product.origen ? "bg-stone-50/80 border-stone-100 shadow-2xs" : "bg-stone-50/30 border-dashed border-stone-200/60 opacity-40 grayscale-[50%]"}`, "class")}> <span class="text-base">🌍</span> <div> <span class="block text-[10px] uppercase font-bold text-stone-400">País / Origen</span> ${product.origen ? renderTemplate`<span class="font-bold text-stone-900">${product.origen}</span>` : renderTemplate`<span class="italic text-stone-400 font-normal text-[11px]">No especificado</span>`} </div> </div> <!-- PROCESO --> <div${addAttribute(`flex items-center gap-2.5 p-3 rounded-xl border transition-all ${product.proceso ? "bg-stone-50/80 border-stone-100 shadow-2xs" : "bg-stone-50/30 border-dashed border-stone-200/60 opacity-40 grayscale-[50%]"}`, "class")}> <span class="text-base">⚙️</span> <div> <span class="block text-[10px] uppercase font-bold text-stone-400">Proceso</span> ${product.proceso ? renderTemplate`<span class="font-bold text-stone-900">${product.proceso}</span>` : renderTemplate`<span class="italic text-stone-400 font-normal text-[11px]">No especificado</span>`} </div> </div> <!-- VARIEDAD --> <div${addAttribute(`flex items-center gap-2.5 p-3 rounded-xl border transition-all ${product.variedad ? "bg-stone-50/80 border-stone-100 shadow-2xs" : "bg-stone-50/30 border-dashed border-stone-200/60 opacity-40 grayscale-[50%]"}`, "class")}> <span class="text-base">🌱</span> <div> <span class="block text-[10px] uppercase font-bold text-stone-400">Variedad</span> ${product.variedad ? renderTemplate`<span class="font-bold text-stone-900">${product.variedad}</span>` : renderTemplate`<span class="italic text-stone-400 font-normal text-[11px]">No especificado</span>`} </div> </div> <!-- ALTITUD --> <div${addAttribute(`flex items-center gap-2.5 p-3 rounded-xl border transition-all ${product.altura_msnm ? "bg-stone-50/80 border-stone-100 shadow-2xs" : "bg-stone-50/30 border-dashed border-stone-200/60 opacity-40 grayscale-[50%]"}`, "class")}> <span class="text-base">⛰️</span> <div> <span class="block text-[10px] uppercase font-bold text-stone-400">Altitud</span> ${product.altura_msnm ? renderTemplate`<span class="font-bold text-stone-900">${product.altura_msnm}</span>` : renderTemplate`<span class="italic text-stone-400 font-normal text-[11px]">No registrada</span>`} </div> </div> <!-- TUESTE Y ESCALA AGTRON --> <div${addAttribute(`flex items-center gap-2.5 p-3 rounded-xl border col-span-2 sm:col-span-1 transition-all ${product.tueste || product.escala_agtron ? "bg-stone-50/80 border-stone-100 shadow-2xs" : "bg-stone-50/30 border-dashed border-stone-200/60 opacity-40 grayscale-[50%]"}`, "class")}> <span class="text-base">🔥</span> <div> <span class="block text-[10px] uppercase font-bold text-stone-400">Tueste / Escala Agtron</span> ${product.tueste || product.escala_agtron ? renderTemplate`<span class="font-bold text-stone-900 flex items-center gap-1.5 flex-wrap"> <span>${product.tueste || "Medio"}</span> ${product.escala_agtron && renderTemplate`<span class="text-[10px] font-extrabold text-emerald-800 bg-emerald-50 border border-emerald-200 px-1.5 py-0.2 rounded-md" title="Nivel en la escala de tueste colorimétrico Agtron SCAA">
Agtron #${product.escala_agtron} </span>`} </span>` : renderTemplate`<span class="italic text-stone-400 font-normal text-[11px]">No especificado</span>`} </div> </div> </div> </div> </div> <!-- SECCIÓN DE PRECIO DESTACADO Y SELECCIÓN DE VARIANTE --> <div class="space-y-4 border-t border-stone-100 pt-5"> <div class="flex items-baseline justify-between bg-stone-50/80 p-4 rounded-2xl border border-stone-200/60"> <div> <span class="block text-[10px] uppercase font-bold tracking-wider text-stone-400">
Precio Formato Seleccionado
</span> <p id="display-unit-price" class="text-2xl sm:text-3xl font-extrabold text-stone-900 tracking-tight">
$${currentPrice.toLocaleString("es-CL")} <span class="text-xs font-semibold text-stone-500">CLP</span> </p> </div> <div class="text-right"> <span class="block text-[10px] uppercase font-bold tracking-wider text-stone-400">
Referencia ($/kg)
</span> <p id="display-kilo-price" class="text-sm sm:text-base font-bold text-emerald-800">
$${currentPriceKilo.toLocaleString("es-CL")} <span class="text-[10px] font-semibold text-emerald-600">/kg</span> </p> </div> </div> <!-- SELECTOR DE FORMATO SI TIENE MÚLTIPLES --> ${product.variantes.length > 1 && renderTemplate`<div> <label for="variant-selector" class="block text-xs font-bold text-stone-600 mb-1.5">
Selecciona Formato y Molienda:
</label> <select id="variant-selector" class="w-full bg-white border border-stone-200 rounded-xl px-3 py-2.5 text-xs font-medium text-stone-800 focus:outline-none focus:ring-2 focus:ring-emerald-600 shadow-2xs"> ${product.variantes.map((v, i) => renderTemplate`<option${addAttribute(i, "value")}${addAttribute(v.id === bestVariant?.id, "selected")}> ${v.formato_gramos}g · ${v.opcion} — $${v.precio_clp.toLocaleString("es-CL")} ($${v.precio_por_kilo.toLocaleString("es-CL")}/kg)
</option>`)} </select> </div>`} <!-- BOTÓN DIRECTO DE COMPRA --> <a id="btn-main-outbound-store"${addAttribute(product.url_detalle, "href")} target="_blank" rel="noopener noreferrer" data-track-outbound="true"${addAttribute(product.tienda, "data-store")}${addAttribute(product.nombre, "data-product-name")}${addAttribute(currentPrice, "data-price")} class="flex items-center justify-center gap-2 w-full bg-emerald-800 hover:bg-emerald-900 text-white font-bold text-center py-3.5 px-6 rounded-2xl shadow-sm transition duration-150 hover:shadow-md"> <span>Ir a comprar en ${product.tienda}</span> <span aria-hidden="true">↗</span> </a> </div> </div> </section> <!-- CU-07: RUEDA DE SABORES SCA Y PERFIL DE COORDENADAS POLARES (RADAR PRIMERO) --> ${renderComponent($$result2, "FlavorWheel", $$FlavorWheel, { "product": product })} <!-- TABLA ESTRUCTURADA DE FORMATOS Y PRECIOS TRANSPARENTADOS (AGRUPADA POR PRECIO) --> <section class="bg-white p-6 sm:p-8 rounded-3xl border border-stone-200/80 shadow-2xs space-y-4"> <div> <h2 class="text-base font-bold text-stone-900">
Formatos y Precios Transparentados
</h2> <p class="text-xs text-stone-400">
Cálculo exacto del costo por kilo agrupado por valor para facilitar la comparación rápida
</p> </div> <div class="overflow-x-auto"> <table class="w-full text-left text-xs border-collapse"> <thead> <tr class="border-b border-stone-200 text-stone-400 uppercase text-[10px] font-bold"> <th class="py-3 px-3">Gramaje</th> <th class="py-3 px-3">Moliendas / Presentaciones</th> <th class="py-3 px-3">Precio Bolsa</th> <th class="py-3 px-3">Precio por Kilo ($/kg)</th> <th class="py-3 px-3 text-right">Disponibilidad</th> </tr> </thead> <tbody class="divide-y divide-stone-100"> ${groupedVariants.map((group) => renderTemplate`<tr${addAttribute(group.disponible ? "hover:bg-stone-50/60 transition-colors" : "opacity-50 bg-stone-50/50", "class")}> <td class="py-3.5 px-3 font-extrabold text-stone-900 text-sm align-top"> ${group.formato_gramos}g
</td> <td class="py-3.5 px-3 align-top"> <div class="flex flex-wrap gap-1.5 max-w-md"> ${group.presentaciones.map((p) => renderTemplate`<span class="inline-flex items-center text-[11px] font-semibold bg-stone-100 text-stone-700 px-2.5 py-0.5 rounded-lg border border-stone-200/70 shadow-2xs"> ${p} </span>`)} </div> </td> <td class="py-3.5 px-3 font-bold text-stone-900 text-sm align-top whitespace-nowrap">
$${group.precio_clp.toLocaleString("es-CL")} ${group.en_oferta && renderTemplate`<span class="block text-[10px] line-through text-stone-400 font-normal">
$${group.precio_original_clp.toLocaleString("es-CL")} </span>`} </td> <td class="py-3.5 px-3 align-top whitespace-nowrap"> <span class="inline-flex items-center gap-1 font-extrabold text-emerald-800 bg-emerald-50 border border-emerald-100 px-2.5 py-1 rounded-lg">
$${group.precio_por_kilo.toLocaleString("es-CL")}/kg
${group.es_estimado && renderTemplate`<span class="rounded bg-amber-100 text-amber-800 px-1 py-0.2 text-[8px] font-bold">Est.</span>`} </span> </td> <td class="py-3.5 px-3 text-right align-top whitespace-nowrap"> <span${addAttribute(`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[10px] font-bold ${group.disponible ? "bg-emerald-50 text-emerald-800" : "bg-stone-100 text-stone-500"}`, "class")}> <span${addAttribute(`h-1.5 w-1.5 rounded-full ${group.disponible ? "bg-emerald-500" : "bg-stone-400"}`, "class")}></span> ${group.disponible ? "Disponible" : "Agotado"} </span> </td> </tr>`)} </tbody> </table> </div> </section> <!-- CU-06: HISTÓRICO Y GRÁFICO DE PRECIOS CON MÉTRICAS SUPERIORES --> <section class="bg-white p-6 sm:p-8 rounded-3xl border border-stone-200/80 shadow-2xs space-y-6"> <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-stone-100 pb-4"> <div> <h2 class="text-base font-bold text-stone-900">Histórico de Precios</h2> <p class="text-xs text-stone-400">Evolución de precios en el tiempo para identificar el mejor momento de compra</p> </div> <!-- TOGGLE MODO GRÁFICO --> <div class="inline-flex rounded-xl border border-stone-200 bg-stone-50 p-1 text-xs font-semibold"> <button id="btn-chart-kilo" class="rounded-lg bg-white shadow-2xs px-3 py-1 text-emerald-800 font-bold transition">
$/kg (Kilo)
</button> <button id="btn-chart-unit" class="rounded-lg px-3 py-1 text-stone-500 hover:text-stone-800 transition">
$ CLP (Bolsa)
</button> </div> </div> <!-- MÉTRICAS CLAVE SUPERIORES --> <div class="grid grid-cols-3 gap-3 sm:gap-4"> <div class="bg-stone-50/70 p-3.5 rounded-2xl border border-stone-100"> <span class="block text-[10px] font-bold uppercase tracking-wider text-stone-400">Precio Actual</span> <p id="metric-current-price" class="text-sm sm:text-lg font-extrabold text-stone-900 mt-0.5">
$${currentPrice.toLocaleString("es-CL")} </p> </div> <div class="bg-stone-50/70 p-3.5 rounded-2xl border border-stone-100"> <span class="block text-[10px] font-bold uppercase tracking-wider text-stone-400">Mínimo Histórico</span> <p id="metric-min-price" class="text-sm sm:text-lg font-extrabold text-emerald-700 mt-0.5">
$${minHistorical.toLocaleString("es-CL")} </p> </div> <div class="bg-stone-50/70 p-3.5 rounded-2xl border border-stone-100"> <span class="block text-[10px] font-bold uppercase tracking-wider text-stone-400">Promedio</span> <p id="metric-avg-price" class="text-sm sm:text-lg font-extrabold text-stone-700 mt-0.5">
$${avgHistorical.toLocaleString("es-CL")} </p> </div> </div> <!-- CONTENEDOR DEL GRÁFICO VECTORIAL INTERACTIVO --> <div class="relative w-full bg-stone-50/50 border border-stone-200/60 rounded-2xl p-4 sm:p-5 flex flex-col justify-between"> <div id="price-chart-svg-wrapper" class="w-full min-h-[170px] relative flex items-center justify-center"> <!-- Renderizado dinámico vía SVG --> </div> <div class="flex items-center justify-between text-[11px] text-stone-400 border-t border-stone-100/80 pt-2.5 mt-2"> <span class="flex items-center gap-1.5 font-medium text-emerald-800"> <span class="h-2 w-2 rounded-full bg-emerald-500 animate-pulse"></span>
Monitoreo en tiempo real
</span> <span id="chart-legend-label" class="font-semibold text-stone-500">
Mostrando: Precio por Kilo ($/kg)
</span> </div> </div> </section> <!-- CU-04: CARRUSEL / GRILLA DE CAFÉS RELACIONADOS (SUSTITUTOS DIRECTOS) --> ${matches.length > 0 && renderTemplate`<section class="bg-white p-6 sm:p-8 rounded-3xl border border-stone-200/80 shadow-2xs space-y-4"> <div> <h2 class="text-base font-bold text-stone-900 flex items-center gap-2"> <span>🔄</span> Cafés Relacionados en Otras Tiendas (Sustitutos directos)
</h2> <p class="text-xs text-stone-400">
Mismo origen y proceso en otros tostadores ordenados por conveniencia ($/kg)
</p> </div> <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4"> ${matches.map((m) => {
    const mVar = m.getBestVariant(true) || m.getBestVariant(false);
    return renderTemplate`<a${addAttribute(`/product/${m.id}`, "href")} class="group flex items-center gap-3.5 p-3.5 rounded-2xl border border-stone-200/80 hover:border-emerald-300 hover:shadow-xs transition bg-white"> <img${addAttribute(m.imagen, "src")}${addAttribute(m.nombre, "alt")} referrerpolicy="no-referrer" onerror="this.onerror=null; this.src='https://images.unsplash.com/photo-1559056199-641a0ac8b55e?q=80&w=400&auto=format&fit=crop';" class="w-16 h-16 object-contain bg-[#F4F3ED] rounded-xl p-1.5 flex-shrink-0 group-hover:scale-105 transition-transform"> <div class="min-w-0 flex-1"> <span class="text-[10px] font-bold text-emerald-800 bg-emerald-50 px-2 py-0.5 rounded-full border border-emerald-100"> ${m.tienda} </span> <p class="text-xs font-bold text-stone-900 truncate mt-1 group-hover:text-emerald-800 transition"> ${m.nombre} </p> <p class="text-xs font-extrabold text-emerald-800 mt-0.5">
$${(mVar?.precio_por_kilo || 0).toLocaleString("es-CL")}/kg
<span class="text-[10px] font-normal text-stone-400">($${mVar?.precio_clp.toLocaleString("es-CL")})</span> </p> </div> </a>`;
  })} </div> </section>`} </div>  <aside id="sticky-purchase-bar" class="fixed bottom-6 left-1/2 -translate-x-1/2 z-30 w-[92%] max-w-3xl bg-white/95 backdrop-blur-md border border-stone-200/90 rounded-2xl p-3.5 shadow-xl flex items-center justify-between gap-4 transition-all duration-300" aria-label="Acción rápida de compra"> <div class="flex items-center gap-3 min-w-0"> <img${addAttribute(product.imagen, "src")}${addAttribute(product.nombre, "alt")} referrerpolicy="no-referrer" onerror="this.onerror=null; this.src='https://images.unsplash.com/photo-1559056199-641a0ac8b55e?q=80&w=400&auto=format&fit=crop';" class="h-10 w-10 object-contain bg-[#F4F3ED] rounded-lg p-0.5 flex-shrink-0 hidden sm:block"> <div class="min-w-0"> <p class="text-xs font-bold text-stone-900 truncate max-w-xs sm:max-w-md"> ${product.nombre} </p> <p class="text-[11px] font-semibold text-emerald-800"> <span id="sticky-kilo-price">$${currentPriceKilo.toLocaleString("es-CL")}/kg</span> <span class="text-stone-400 font-normal"> · ${product.tienda}</span> </p> </div> </div> <div class="flex items-center gap-3 flex-shrink-0"> <a id="btn-sticky-outbound"${addAttribute(product.url_detalle, "href")} target="_blank" rel="noopener noreferrer" data-track-outbound="true"${addAttribute(product.tienda, "data-store")}${addAttribute(product.nombre, "data-product-name")}${addAttribute(currentPrice, "data-price")} class="bg-emerald-800 hover:bg-emerald-900 text-white font-bold text-xs py-2.5 px-4 rounded-xl shadow-sm transition"> <span>Comprar en ${product.tienda} ↗</span> </a> </div> </aside> ` }), defineScriptVars({ variantsJson, product }), renderScript($$result, "C:/Users/niko_/OneDrive/Desktop/cafe-sitios/astro-frontend/src/pages/product/[id].astro?astro&type=script&index=0&lang.ts"));
}, "C:/Users/niko_/OneDrive/Desktop/cafe-sitios/astro-frontend/src/pages/product/[id].astro", void 0);

const $$file = "C:/Users/niko_/OneDrive/Desktop/cafe-sitios/astro-frontend/src/pages/product/[id].astro";
const $$url = "/product/[id]";

const _page = /*#__PURE__*/Object.freeze(/*#__PURE__*/Object.defineProperty({
  __proto__: null,
  default: $$id,
  file: $$file,
  url: $$url
}, Symbol.toStringTag, { value: 'Module' }));

const page = () => _page;

export { page };
