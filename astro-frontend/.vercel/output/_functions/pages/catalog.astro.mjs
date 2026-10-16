import { e as createComponent, m as maybeRenderHead, r as renderTemplate, g as addAttribute, l as renderScript, h as createAstro, k as renderComponent } from '../chunks/astro/server_D990-clo.mjs';
import 'piccolore';
import { $ as $$BaseLayout } from '../chunks/BaseLayout_BWXSiVi2.mjs';
import { G as GetCatalogUseCase, $ as $$ProductCard } from '../chunks/GetCatalog_DPd58Pbo.mjs';
import 'clsx';
import { G as GetStoresUseCase } from '../chunks/GetStores_DogB9-iT.mjs';
import { H as HttpClient } from '../chunks/HttpClient_Dd_rjSA5.mjs';
export { renderers } from '../renderers.mjs';

const $$Astro$1 = createAstro();
const $$FiltersAside = createComponent(($$result, $$props, $$slots) => {
  const Astro2 = $$result.createAstro($$Astro$1, $$props, $$slots);
  Astro2.self = $$FiltersAside;
  const {
    stores = [],
    selectedStore = "",
    initialSearch = "",
    initialSort = "kilo",
    initialMinPrice = "",
    initialMaxPrice = "",
    initialCountry = "",
    initialProcess = "",
    initialVariety = "",
    initialNotes = "",
    initialCategory = "cafe"
  } = Astro2.props;
  const sortedStores = [...stores].sort(
    (a, b) => a.nombre.localeCompare(b.nombre, "es", { sensitivity: "base" })
  );
  const hasActiveFilters = Boolean(
    initialSearch || selectedStore || initialCountry || initialProcess || initialVariety || initialNotes || initialMinPrice || initialMaxPrice || initialCategory && initialCategory !== "cafe" || initialSort && initialSort !== "kilo"
  );
  return renderTemplate`${maybeRenderHead()}<aside class="space-y-6"> <section class="bg-white rounded-2xl border border-stone-200/80 p-5 shadow-2xs space-y-5"> <div class="flex items-center justify-between border-b border-stone-100 pb-3"> <div class="flex items-center gap-2"> <span class="text-xs font-bold uppercase tracking-wider text-stone-500">Filtros</span> ${hasActiveFilters && renderTemplate`<span class="h-1.5 w-1.5 rounded-full bg-emerald-600"></span>`} </div> ${hasActiveFilters && renderTemplate`<a href="/catalog" class="text-xs font-medium text-emerald-700 hover:text-emerald-900 transition hover:underline">
Limpiar todo
</a>`} </div> <form id="filters-form" method="GET" action="/catalog" class="space-y-5"> <!-- BUSCADOR SEMÁNTICO (CU-01 / RN-01) --> <div> <label for="catalog-search-input" class="block text-[11px] font-bold uppercase tracking-wider text-stone-400 mb-1.5">
Buscar café o nota
</label> <div class="relative"> <input type="text" name="q" id="catalog-search-input"${addAttribute(initialSearch, "value")} placeholder="Ej. Geisha, Bourbon, Frutal..." class="w-full bg-stone-50/80 border border-stone-200 rounded-lg pl-8 pr-3 py-2 text-xs text-stone-800 placeholder-stone-400 focus:bg-white focus:outline-none focus:ring-2 focus:ring-emerald-600/20 focus:border-emerald-600 transition"> <span class="absolute left-2.5 top-2 text-stone-400 text-xs pointer-events-none" aria-hidden="true">
🔍
</span> </div> </div> <!-- SELECTOR DE CATEGORÍA --> <div> <label for="catalog-category-select" class="block text-[11px] font-bold uppercase tracking-wider text-stone-400 mb-1.5">
Categoría
</label> <select name="category" id="catalog-category-select" class="w-full bg-stone-50/80 border border-stone-200 rounded-lg px-3 py-2 text-xs font-medium text-stone-700 focus:bg-white focus:outline-none focus:ring-2 focus:ring-emerald-600/20 focus:border-emerald-600 transition"> <option value="cafe"${addAttribute(initialCategory === "cafe", "selected")}>☕ Solo Café de Especialidad</option> <option value="no_cafe"${addAttribute(initialCategory === "no_cafe", "selected")}>🎁 Ropa, Cajas y Accesorios</option> <option value="todos"${addAttribute(initialCategory === "todos", "selected")}>🌐 Todo el Catálogo</option> </select> </div> <!-- SELECTOR DE ORDENAMIENTO --> <div> <label for="catalog-sort-select" class="block text-[11px] font-bold uppercase tracking-wider text-stone-400 mb-1.5">
Ordenar Por
</label> <select name="sort_by" id="catalog-sort-select" class="w-full bg-stone-50/80 border border-stone-200 rounded-lg px-3 py-2 text-xs font-medium text-stone-700 focus:bg-white focus:outline-none focus:ring-2 focus:ring-emerald-600/20 focus:border-emerald-600 transition"> <option value="unit"${addAttribute(initialSort === "unit", "selected")}>🏷️ Menor precio por Bolsa/Formato</option> <option value="kilo"${addAttribute(initialSort === "kilo", "selected")}>🌱 Menor $/kg (Más conveniente)</option> <option value="created_desc"${addAttribute(initialSort === "created_desc", "selected")}>✨ Novedades / Recientes</option> </select> </div> <!-- FILTRO DE TIENDAS (CHECKBOXES / RADIOS LIMPIOS) --> ${sortedStores.length > 0 && renderTemplate`<div class="border-t border-stone-100 pt-3"> <span class="block text-[11px] font-bold uppercase tracking-wider text-stone-400 mb-2">
Tostadurías y Tiendas
</span> <div class="max-h-48 overflow-y-auto space-y-1.5 pr-1 text-xs"> <label class="flex items-center justify-between text-stone-600 hover:text-stone-900 cursor-pointer select-none py-0.5 group"> <div class="flex items-center gap-2"> <input type="radio" name="store_name" value=""${addAttribute(!selectedStore, "checked")} class="h-3.5 w-3.5 text-emerald-700 border-stone-300 focus:ring-emerald-500"> <span class="font-medium text-stone-700">Todos</span> </div> </label> ${sortedStores.map((store) => {
    const isSelected = selectedStore === store.nombre;
    return renderTemplate`<label class="flex items-center justify-between text-stone-600 hover:text-stone-900 cursor-pointer select-none py-0.5 group"> <div class="flex items-center gap-2 min-w-0"> <input type="radio" name="store_name"${addAttribute(store.nombre, "value")}${addAttribute(isSelected, "checked")} class="h-3.5 w-3.5 text-emerald-700 border-stone-300 focus:ring-emerald-500"> <span${addAttribute(`truncate ${isSelected ? "font-bold text-emerald-800" : ""}`, "class")}> ${store.nombre} </span> </div> <span class="text-[10px] font-semibold text-stone-400 group-hover:text-stone-600 flex-shrink-0 ml-1"> ${store.cantidad_productos} </span> </label>`;
  })} </div> </div>`} <!-- FILTROS AVANZADOS / FACETAS DESPLEGABLES --> <div class="border-t border-stone-100 pt-3"> <button id="btn-toggle-adv-filters" type="button" class="flex w-full items-center justify-between text-xs font-semibold text-stone-700 hover:text-emerald-800 transition py-1"> <span class="flex items-center gap-1.5"> <span>⚙️</span> <span>Origen, Proceso y Precios</span> </span> <span id="adv-arrow" class="text-stone-400 text-[10px] transition-transform">▼</span> </button> <div id="adv-filters-drawer" class="hidden mt-3 space-y-3 pt-2 border-t border-stone-100/60"> <!-- PAÍS DE ORIGEN --> <div> <label for="input-country" class="block text-[10px] font-bold uppercase text-stone-400 mb-1">
País de Origen
</label> <input type="text" name="country" id="input-country"${addAttribute(initialCountry, "value")} placeholder="Ej. Etiopía, Colombia, Kenia..." class="w-full bg-stone-50/80 border border-stone-200 rounded-lg px-2.5 py-1.5 text-xs text-stone-800 focus:bg-white focus:outline-none focus:ring-2 focus:ring-emerald-600/20 focus:border-emerald-600"> </div> <!-- PROCESO --> <div> <label for="input-process" class="block text-[10px] font-bold uppercase text-stone-400 mb-1">
Proceso
</label> <input type="text" name="process" id="input-process"${addAttribute(initialProcess, "value")} placeholder="Lavado, Natural, Anaeróbico..." class="w-full bg-stone-50/80 border border-stone-200 rounded-lg px-2.5 py-1.5 text-xs text-stone-800 focus:bg-white focus:outline-none focus:ring-2 focus:ring-emerald-600/20 focus:border-emerald-600"> </div> <!-- VARIEDAD --> <div> <label for="input-variety" class="block text-[10px] font-bold uppercase text-stone-400 mb-1">
Variedad Botánica
</label> <input type="text" name="variety" id="input-variety"${addAttribute(initialVariety, "value")} placeholder="Caturra, Bourbon, Geisha..." class="w-full bg-stone-50/80 border border-stone-200 rounded-lg px-2.5 py-1.5 text-xs text-stone-800 focus:bg-white focus:outline-none focus:ring-2 focus:ring-emerald-600/20 focus:border-emerald-600"> </div> <!-- NOTAS DE CATA --> <div> <label for="input-notes" class="block text-[10px] font-bold uppercase text-stone-400 mb-1">
Notas Sensoriales
</label> <input type="text" name="notes" id="input-notes"${addAttribute(initialNotes, "value")} placeholder="Ej. chocolate, jazmín, cítrico..." class="w-full bg-stone-50/80 border border-stone-200 rounded-lg px-2.5 py-1.5 text-xs text-stone-800 focus:bg-white focus:outline-none focus:ring-2 focus:ring-emerald-600/20 focus:border-emerald-600"> </div> <!-- RANGO DE PRECIO --> <div class="grid grid-cols-2 gap-2"> <div> <label for="input-min-price" class="block text-[10px] font-bold uppercase text-stone-400 mb-1">
Min ($)
</label> <input type="number" name="min_price" id="input-min-price"${addAttribute(initialMinPrice, "value")} placeholder="10000" class="w-full bg-stone-50/80 border border-stone-200 rounded-lg px-2.5 py-1.5 text-xs text-stone-800"> </div> <div> <label for="input-max-price" class="block text-[10px] font-bold uppercase text-stone-400 mb-1">
Max ($)
</label> <input type="number" name="max_price" id="input-max-price"${addAttribute(initialMaxPrice, "value")} placeholder="35000" class="w-full bg-stone-50/80 border border-stone-200 rounded-lg px-2.5 py-1.5 text-xs text-stone-800"> </div> </div> </div> </div> <!-- BOTÓN DE APLICAR FILTROS --> <button type="submit" class="w-full bg-stone-900 hover:bg-emerald-900 text-white font-semibold py-2.5 px-4 rounded-xl text-xs transition duration-150 shadow-sm">
Aplicar Filtros
</button> </form> </section> </aside> ${renderScript($$result, "C:/Users/niko_/OneDrive/Desktop/cafe-sitios/astro-frontend/src/components/catalog/FiltersAside.astro?astro&type=script&index=0&lang.ts")}`;
}, "C:/Users/niko_/OneDrive/Desktop/cafe-sitios/astro-frontend/src/components/catalog/FiltersAside.astro", void 0);

const $$RecentlyViewed = createComponent(($$result, $$props, $$slots) => {
  return renderTemplate`<!-- CU-10: VISTOS RECIENTEMENTE (FIFO LOCALSTORAGE) -->${maybeRenderHead()}<section id="recently-viewed-panel" class="hidden bg-white rounded-2xl border border-stone-200/80 p-5 shadow-2xs"> <div class="flex items-center justify-between gap-3 mb-3 border-b border-stone-100 pb-2.5"> <h2 class="text-xs font-bold uppercase tracking-wider text-stone-400 flex items-center gap-1.5"> <span>🕒</span> <span>Vistos Recientemente</span> </h2> <button type="button" id="btn-clear-recently-viewed" class="text-[11px] font-medium text-stone-400 hover:text-stone-700 transition">
Borrar
</button> </div> <div id="recently-viewed-items" class="space-y-2"></div> </section> ${renderScript($$result, "C:/Users/niko_/OneDrive/Desktop/cafe-sitios/astro-frontend/src/components/catalog/RecentlyViewed.astro?astro&type=script&index=0&lang.ts")}`;
}, "C:/Users/niko_/OneDrive/Desktop/cafe-sitios/astro-frontend/src/components/catalog/RecentlyViewed.astro", void 0);

const $$Astro = createAstro();
const $$Catalog = createComponent(async ($$result, $$props, $$slots) => {
  const Astro2 = $$result.createAstro($$Astro, $$props, $$slots);
  Astro2.self = $$Catalog;
  const url = new URL(Astro2.request.url);
  const searchQuery = url.searchParams.get("q") || url.searchParams.get("search_query") || "";
  const sortBy = url.searchParams.get("sort_by") || "kilo";
  const category = url.searchParams.get("category") || "cafe";
  const storeName = url.searchParams.get("store_name") || "";
  const process = url.searchParams.get("process") || "";
  const country = url.searchParams.get("country") || "";
  const variety = url.searchParams.get("variety") || "";
  const notes = url.searchParams.get("notes") || "";
  const minPrice = url.searchParams.get("min_price") ? Number(url.searchParams.get("min_price")) : void 0;
  const maxPrice = url.searchParams.get("max_price") ? Number(url.searchParams.get("max_price")) : void 0;
  const catalogUseCase = new GetCatalogUseCase();
  const storesUseCase = new GetStoresUseCase();
  const http = new HttpClient();
  let items = [];
  let totalItems = 0;
  let stores = [];
  let lastSyncTime = "Al d\xEDa";
  try {
    const [catalogRes, storesRes, syncRes] = await Promise.allSettled([
      catalogUseCase.execute({
        searchQuery,
        sortBy: sortBy === "created_desc" ? "kilo" : sortBy,
        category,
        storeName,
        process,
        country,
        variety,
        notes,
        minPrice,
        maxPrice,
        limit: 18,
        offset: 0
      }),
      storesUseCase.execute({ pageSize: 50, sortBy: "name_asc" }),
      http.get("/api/v1/sync/last")
    ]);
    if (catalogRes.status === "fulfilled") {
      items = catalogRes.value.items;
      totalItems = catalogRes.value.total;
    }
    if (storesRes.status === "fulfilled") {
      stores = storesRes.value;
    }
    if (syncRes.status === "fulfilled" && syncRes.value.last_sync) {
      lastSyncTime = new Date(syncRes.value.last_sync).toLocaleString("es-CL", {
        day: "2-digit",
        month: "2-digit",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit"
      }) + " hrs";
    }
  } catch (error) {
    console.error("Error cargando cat\xE1logo en SSR:", error);
  }
  const activeFilters = [];
  if (searchQuery) activeFilters.push({ label: `"${searchQuery}"`, paramKey: "q" });
  if (category !== "cafe") {
    activeFilters.push({
      label: category === "no_cafe" ? "\u{1F381} Ropa / Accesorios" : "\u{1F310} Todo el Cat\xE1logo",
      paramKey: "category"
    });
  }
  if (storeName) activeFilters.push({ label: `Tienda: ${storeName}`, paramKey: "store_name" });
  if (country) activeFilters.push({ label: `Origen: ${country}`, paramKey: "country" });
  if (process) activeFilters.push({ label: `Proceso: ${process}`, paramKey: "process" });
  if (variety) activeFilters.push({ label: `Variedad: ${variety}`, paramKey: "variety" });
  if (notes) activeFilters.push({ label: `Nota: ${notes}`, paramKey: "notes" });
  if (minPrice || maxPrice) {
    const p = [minPrice ? `$${minPrice.toLocaleString("es-CL")}` : "", maxPrice ? `$${maxPrice.toLocaleString("es-CL")}` : ""].filter(Boolean).join(" - ");
    activeFilters.push({ label: `Precio: ${p}`, paramKey: "price" });
  }
  const jsonLdCatalog = {
    "@context": "https://schema.org",
    "@type": "ItemList",
    "name": "Cat\xE1logo de Caf\xE9 de Especialidad en Chile",
    "description": "Lista de caf\xE9s de especialidad disponibles en tostadur\xEDas chilenas ordenados por $/kg y atributos bot\xE1nicos.",
    "numberOfItems": totalItems,
    "itemListElement": items.slice(0, 10).map((prod, index) => ({
      "@type": "ListItem",
      "position": index + 1,
      "item": {
        "@type": "Product",
        "name": prod.nombre,
        "image": prod.imagen,
        "brand": { "@type": "Brand", "name": prod.tienda },
        "offers": {
          "@type": "Offer",
          "priceCurrency": "CLP",
          "price": prod.variante?.precio_clp || 0,
          "availability": prod.variante?.disponible ? "https://schema.org/InStock" : "https://schema.org/OutOfStock",
          "url": prod.url_detalle
        }
      }
    }))
  };
  return renderTemplate`${renderComponent($$result, "BaseLayout", $$BaseLayout, { "title": "Cat\xE1logo de Caf\xE9 de Especialidad en Chile | Precios por Kilo y Tiendas | Cafesitios", "description": "Compara en tiempo real los precios por kilo ($/kg), or\xEDgenes, procesos y formatos de las principales tostadur\xEDas de caf\xE9 de especialidad en Chile.", "canonicalUrl": "https://cafesitios.cl/catalog", "jsonLd": jsonLdCatalog, "lastSync": lastSyncTime }, { "default": async ($$result2) => renderTemplate` ${maybeRenderHead()}<div class="grid grid-cols-1 lg:grid-cols-[280px_minmax(0,1fr)] xl:grid-cols-[300px_minmax(0,1fr)] gap-8 items-start"> <!-- SIDEBAR UNIFICADO (Filtros facetados + Vistos recientemente) --> <div class="space-y-6"> ${renderComponent($$result2, "FiltersAside", $$FiltersAside, { "stores": stores, "selectedStore": storeName, "initialSearch": searchQuery, "initialSort": sortBy, "initialCategory": category, "initialMinPrice": minPrice ? String(minPrice) : "", "initialMaxPrice": maxPrice ? String(maxPrice) : "", "initialCountry": country, "initialProcess": process, "initialVariety": variety, "initialNotes": notes })} ${renderComponent($$result2, "RecentlyViewed", $$RecentlyViewed, {})} </div> <!-- ÁREA PRINCIPAL DE CATÁLOGO --> <section class="min-w-0 space-y-6"> <!-- HERO / BANNER DTC SOBRIO --> <div class="relative overflow-hidden rounded-3xl bg-gradient-to-br from-stone-900 via-stone-850 to-stone-900 p-6 sm:p-8 text-white shadow-sm border border-stone-800"> <div class="relative z-10 max-w-xl space-y-2"> <span class="inline-flex items-center gap-1.5 rounded-full bg-emerald-950/80 border border-emerald-500/30 px-3 py-1 text-[10px] font-bold uppercase tracking-wider text-emerald-400"> <span>✨</span> Transparencia y Ahorro Inteligente
</span> <h1 class="text-xl sm:text-2xl font-extrabold tracking-tight text-white leading-tight">
Encuentra el mejor precio por kilo ($/kg) en café de especialidad
</h1> <p class="text-xs sm:text-sm text-stone-300 font-normal leading-relaxed">
Comparamos orígenes, procesos, notas y formatos de tostadurías chilenas para que compres informado al costo real por gramo.
</p> </div> <!-- Elemento decorativo visual sutil --> <div class="absolute -right-8 -bottom-10 opacity-10 pointer-events-none select-none text-9xl">
☕
</div> </div> <!-- HEADER DE RESULTADOS Y ACTIVE FILTER TAGS --> <div class="bg-white p-4 sm:p-5 rounded-2xl border border-stone-200/80 shadow-2xs space-y-3"> <div class="flex flex-wrap items-center justify-between gap-3"> <div> <h2 class="text-sm font-bold text-stone-900"> ${category === "no_cafe" ? "\u{1F381} Ropa, Cajas y Accesorios" : activeFilters.length > 0 ? "Caf\xE9s Filtrados" : "Cat\xE1logo de Especialidad"} </h2> <p class="text-xs text-stone-400">
Mostrando <strong id="catalog-count-current" class="text-stone-700 font-semibold">${items.length}</strong> de <span id="catalog-count-total">${totalItems}</span> productos
</p> </div> ${activeFilters.length > 0 && renderTemplate`<a href="/catalog" class="inline-flex items-center gap-1.5 text-xs font-semibold text-emerald-800 hover:text-emerald-950 bg-emerald-50/70 border border-emerald-100 px-3 py-1.5 rounded-xl transition"> <span>✕</span> Limpiar filtros
</a>`} </div> <!-- TAGS DE FILTROS ACTIVOS --> ${activeFilters.length > 0 && renderTemplate`<div class="flex flex-wrap gap-1.5 pt-2 border-t border-stone-100"> ${activeFilters.map((filter) => renderTemplate`<span class="inline-flex items-center gap-1 rounded-lg bg-stone-100 text-stone-700 px-2.5 py-1 text-[11px] font-medium"> <span>${filter.label}</span> </span>`)} </div>`} </div> <!-- GRILLA DE PRODUCTOS RESPONSIVE CON SCROLL INFINITO --> ${items.length === 0 ? renderTemplate`<div class="bg-white p-12 text-center rounded-3xl border border-stone-200/70 text-slate-400 space-y-3 shadow-2xs"> <p class="text-3xl">☕</p> <h3 class="text-sm font-bold text-stone-800">No encontramos productos que coincidan con estos filtros</h3> <p class="text-xs text-stone-500 max-w-sm mx-auto">
Intenta eliminar algunos filtros en la barra lateral o cambiar de categoría.
</p> <div class="pt-2"> <a href="/catalog" class="inline-block bg-stone-900 hover:bg-emerald-900 text-white font-semibold text-xs px-4 py-2.5 rounded-xl transition">
Ver todo el catálogo
</a> </div> </div>` : renderTemplate`<div id="products-grid" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-2 xl:grid-cols-3 gap-6"${addAttribute(totalItems, "data-total")}${addAttribute(items.length, "data-loaded")}${addAttribute(sortBy, "data-sort")}${addAttribute(category, "data-category")}${addAttribute(searchQuery, "data-search")}${addAttribute(storeName, "data-store")}${addAttribute(country, "data-country")}${addAttribute(process, "data-process")}${addAttribute(variety, "data-variety")}${addAttribute(notes, "data-notes")}${addAttribute(minPrice || "", "data-min-price")}${addAttribute(maxPrice || "", "data-max-price")}> ${items.map((product) => renderTemplate`${renderComponent($$result2, "ProductCard", $$ProductCard, { "product": product })}`)} </div>`} <!-- TRIGGER ELEMENT Y SPINNER PARA SCROLL INFINITO --> <div id="infinite-scroll-sentinel" class="py-10 flex flex-col items-center justify-center min-h-[100px]"> <!-- ESTADO DE CARGA VISUAL (SPINNER + FEEDBACK CLARO) --> <div id="infinite-loading-spinner" class="hidden flex-col sm:flex-row items-center gap-3.5 bg-white border border-stone-200/90 shadow-sm px-6 py-4 rounded-2xl text-stone-700"> <div class="relative flex items-center justify-center"> <svg class="animate-spin h-6 w-6 text-emerald-700" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"> <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle> <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"></path> </svg> <span class="absolute text-[10px]">☕</span> </div> <div class="text-center sm:text-left"> <p class="text-xs font-bold text-stone-900">
Cargando más cafés de especialidad...
</p> <p class="text-[11px] text-stone-500 font-normal">
Consultando catálogo y tostadurías chilenas
</p> </div> </div> <!-- ERROR STATE CON BOTÓN REINTENTAR --> <div id="infinite-error-container" class="hidden flex-col items-center gap-2.5 bg-amber-50/80 border border-amber-200 px-6 py-4 rounded-2xl text-center max-w-md"> <p class="text-xs text-amber-900 font-medium">
⚠️ No pudimos cargar más cafés en este momento.
</p> <button type="button" id="infinite-retry-btn" class="inline-flex items-center gap-1.5 text-xs font-bold bg-amber-800 hover:bg-amber-900 text-white px-4 py-1.5 rounded-xl transition shadow-2xs cursor-pointer"> <span>🔄 Reintentar cargar más</span> </button> </div> <!-- MENSAJE DE FIN DE CATÁLOGO --> <div id="infinite-end-msg"${addAttribute(items.length >= totalItems && totalItems > 0 ? "flex flex-col items-center gap-2 text-center" : "hidden flex-col items-center gap-2 text-center", "class")}> <p class="text-stone-400 text-xs font-medium">
☕ Has explorado todos los cafés disponibles para esta selección
</p> <button type="button" id="scroll-to-top-btn" class="text-[11px] font-semibold text-emerald-800 hover:text-emerald-950 underline underline-offset-2 cursor-pointer transition">
↑ Volver al inicio de la página
</button> </div> </div> </section> </div> ` })} ${renderScript($$result, "C:/Users/niko_/OneDrive/Desktop/cafe-sitios/astro-frontend/src/pages/catalog.astro?astro&type=script&index=0&lang.ts")}`;
}, "C:/Users/niko_/OneDrive/Desktop/cafe-sitios/astro-frontend/src/pages/catalog.astro", void 0);

const $$file = "C:/Users/niko_/OneDrive/Desktop/cafe-sitios/astro-frontend/src/pages/catalog.astro";
const $$url = "/catalog";

const _page = /*#__PURE__*/Object.freeze(/*#__PURE__*/Object.defineProperty({
  __proto__: null,
  default: $$Catalog,
  file: $$file,
  url: $$url
}, Symbol.toStringTag, { value: 'Module' }));

const page = () => _page;

export { page };
