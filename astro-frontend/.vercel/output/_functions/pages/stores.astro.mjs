import { e as createComponent, k as renderComponent, l as renderScript, r as renderTemplate, h as createAstro, o as Fragment, m as maybeRenderHead, g as addAttribute } from '../chunks/astro/server_D990-clo.mjs';
import 'piccolore';
import { $ as $$BaseLayout } from '../chunks/BaseLayout_BWXSiVi2.mjs';
import { G as GetStoresUseCase } from '../chunks/GetStores_DogB9-iT.mjs';
/* empty css                                  */
export { renderers } from '../renderers.mjs';

var __freeze = Object.freeze;
var __defProp = Object.defineProperty;
var __template = (cooked, raw) => __freeze(__defProp(cooked, "raw", { value: __freeze(cooked.slice()) }));
var _a;
const $$Astro = createAstro();
const $$Stores = createComponent(async ($$result, $$props, $$slots) => {
  const Astro2 = $$result.createAstro($$Astro, $$props, $$slots);
  Astro2.self = $$Stores;
  const url = new URL(Astro2.request.url);
  const sortBy = url.searchParams.get("sort_by") || "product_count_desc";
  const lat = url.searchParams.get("lat") ? Number(url.searchParams.get("lat")) : void 0;
  const lon = url.searchParams.get("lon") ? Number(url.searchParams.get("lon")) : void 0;
  const storesUseCase = new GetStoresUseCase();
  let stores = [];
  try {
    stores = await storesUseCase.execute({
      pageSize: 100,
      sortBy,
      lat,
      lon
    });
  } catch (error) {
    console.error("Error cargando tiendas en SSR:", error);
  }
  return renderTemplate`${renderComponent($$result, "BaseLayout", $$BaseLayout, { "title": "Mapa y Directorio de Tostadur\xEDas de Caf\xE9 en Chile | Cafesitios", "description": "Mapa interactivo y directorio de tostadur\xEDas de caf\xE9 de especialidad integradas en Cafesitios. Ubica tostadores en Providencia, Santiago, Las Condes y regiones.", "data-astro-cid-ypbxk3ea": true }, { "default": async ($$result2) => renderTemplate`  ${maybeRenderHead()}<div class="space-y-8" data-astro-cid-ypbxk3ea> <!-- BREADCRUMB --> <nav class="flex items-center gap-2 text-xs text-stone-500" data-astro-cid-ypbxk3ea> <a href="/" class="hover:text-emerald-800 transition" data-astro-cid-ypbxk3ea>Catálogo</a> <span class="text-stone-300" data-astro-cid-ypbxk3ea>/</span> <span class="font-semibold text-stone-800" data-astro-cid-ypbxk3ea>Mapa y Directorio de Tiendas</span> </nav> <!-- HEADER DE SECCIÓN Y CONTROLES --> <div class="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-white p-6 sm:p-8 rounded-3xl border border-stone-200/80 shadow-2xs" data-astro-cid-ypbxk3ea> <div class="space-y-1" data-astro-cid-ypbxk3ea> <h1 class="text-xl sm:text-2xl font-extrabold tracking-tight text-stone-900" data-astro-cid-ypbxk3ea>
Mapa de Tostadurías de Especialidad
</h1> <p class="text-xs text-stone-500" data-astro-cid-ypbxk3ea>
Explora tostadurías físicas y marcas asociadas en Chile con monitoreo en tiempo real (<strong class="text-stone-800 font-semibold" data-astro-cid-ypbxk3ea>${stores.length} tiendas</strong>).
</p> </div> <!-- BOTONES DE ORDEN Y GPS --> <div class="flex flex-wrap items-center gap-2.5" data-astro-cid-ypbxk3ea> <button id="btn-detect-gps" type="button" class="inline-flex items-center gap-1.5 rounded-xl border border-emerald-200 bg-emerald-50 px-3.5 py-2 text-xs font-semibold text-emerald-800 hover:bg-emerald-100 transition shadow-2xs" data-astro-cid-ypbxk3ea> <span data-astro-cid-ypbxk3ea>📍</span> Centrar en mi ubicación GPS
</button> <button id="btn-toggle-map" type="button" class="inline-flex items-center gap-1.5 rounded-xl border border-stone-200 bg-white px-3.5 py-2 text-xs font-semibold text-stone-700 hover:bg-stone-50 transition shadow-2xs" data-astro-cid-ypbxk3ea> <span data-astro-cid-ypbxk3ea>🗺️</span> <span id="toggle-map-text" data-astro-cid-ypbxk3ea>Ocultar Mapa</span> </button> </div> </div> <!-- CONTENEDOR DEL MAPA INTERACTIVO (LEAFLET.JS) --> <div id="map-section" class="bg-white p-3.5 rounded-3xl border border-stone-200/80 shadow-2xs space-y-3" data-astro-cid-ypbxk3ea> <div class="flex items-center justify-between px-2 pt-1 text-xs text-stone-500" data-astro-cid-ypbxk3ea> <span class="font-semibold flex items-center gap-1.5 text-stone-800" data-astro-cid-ypbxk3ea> <span data-astro-cid-ypbxk3ea>📍</span> Ubicación Geográfica de Tiendas y Tostadores
</span> <span class="text-[11px] text-stone-400" data-astro-cid-ypbxk3ea>
Haz clic en cualquier pin para ver cafés disponibles y sitio web
</span> </div> <div id="stores-map" class="h-80 sm:h-96 w-full rounded-2xl z-10 border border-stone-100"${addAttribute(JSON.stringify(stores), "data-stores")} data-astro-cid-ypbxk3ea></div> </div> <!-- FILTRO RÁPIDO Y BUSCADOR DE TIENDAS --> <div class="flex flex-col sm:flex-row items-center justify-between gap-3 bg-white p-4 rounded-2xl border border-stone-200/80 shadow-2xs" data-astro-cid-ypbxk3ea> <div class="relative w-full sm:w-72" data-astro-cid-ypbxk3ea> <input type="text" id="store-search-filter" placeholder="Filtrar por nombre o comuna..." class="w-full bg-stone-50 border border-stone-200 rounded-xl pl-8 pr-3 py-2 text-xs text-stone-800 focus:bg-white focus:outline-none focus:ring-2 focus:ring-emerald-600/20 focus:border-emerald-600 transition" data-astro-cid-ypbxk3ea> <span class="absolute left-2.5 top-2.5 text-stone-400 text-xs pointer-events-none" data-astro-cid-ypbxk3ea>🔍</span> </div> <div class="flex items-center gap-2 text-xs text-stone-400 w-full sm:w-auto justify-end" data-astro-cid-ypbxk3ea> <span data-astro-cid-ypbxk3ea>Mostrando <strong id="store-count-display" class="text-stone-700 font-semibold" data-astro-cid-ypbxk3ea>${stores.length}</strong> tostadurías</span> </div> </div> <!-- GRILLA DE TIENDAS --> <div id="stores-cards-grid" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6" data-astro-cid-ypbxk3ea> ${stores.map((tienda) => renderTemplate`<article class="store-card bg-white rounded-2xl border border-stone-200/80 p-5 shadow-2xs hover:border-emerald-300 hover:shadow-xs transition flex flex-col justify-between"${addAttribute(tienda.nombre.toLowerCase(), "data-name")}${addAttribute((tienda.comuna || "").toLowerCase(), "data-comuna")}${addAttribute(tienda.latitud, "data-lat")}${addAttribute(tienda.longitud, "data-lon")} data-astro-cid-ypbxk3ea> <div class="space-y-3" data-astro-cid-ypbxk3ea> <div class="flex items-center justify-between" data-astro-cid-ypbxk3ea> <h2 class="text-sm font-bold text-stone-900" data-astro-cid-ypbxk3ea>${tienda.nombre}</h2> <span class="bg-emerald-50 text-emerald-800 text-[10px] font-extrabold px-2 py-0.5 rounded-full border border-emerald-100" data-astro-cid-ypbxk3ea> ${tienda.cantidad_productos} cafés
</span> </div> <div class="space-y-1.5 text-xs text-stone-500" data-astro-cid-ypbxk3ea> ${tienda.comuna && renderTemplate`<p class="flex items-center gap-1.5" data-astro-cid-ypbxk3ea> <span class="text-stone-400" data-astro-cid-ypbxk3ea>📍</span> <span class="font-medium text-stone-700" data-astro-cid-ypbxk3ea>${tienda.comuna}</span> </p>`} ${tienda.distancia_km !== void 0 && tienda.distancia_km !== null && renderTemplate`<p class="font-bold text-emerald-700" data-astro-cid-ypbxk3ea>
Cercanía estimada: ~${tienda.distancia_km} km
</p>`} ${tienda.plataforma && renderTemplate`<p class="text-[10px] text-stone-400" data-astro-cid-ypbxk3ea>
Plataforma: ${tienda.plataforma} </p>`} </div> </div> <div class="pt-4 mt-4 border-t border-stone-100 flex items-center justify-between gap-2" data-astro-cid-ypbxk3ea> <a${addAttribute(`/?store_name=${encodeURIComponent(tienda.nombre)}`, "href")} class="text-xs font-semibold text-emerald-800 hover:underline" data-astro-cid-ypbxk3ea>
Ver cafés disponibles →
</a> ${tienda.url_web && renderTemplate`<a${addAttribute(tienda.url_web, "href")} target="_blank" rel="noopener noreferrer" class="text-xs text-stone-400 hover:text-stone-600 transition" data-astro-cid-ypbxk3ea>
Sitio oficial ↗
</a>`} </div> </article>`)} </div> </div> `, "head": async ($$result2) => renderTemplate`${renderComponent($$result2, "Fragment", Fragment, { "slot": "head" }, { "default": async ($$result3) => renderTemplate(_a || (_a = __template([' <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" integrity="sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY=" crossorigin=""> <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js" integrity="sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo=" crossorigin=""><\/script>  ']))) })}` })} ${renderScript($$result, "C:/Users/niko_/OneDrive/Desktop/cafe-sitios/astro-frontend/src/pages/stores.astro?astro&type=script&index=0&lang.ts")}`;
}, "C:/Users/niko_/OneDrive/Desktop/cafe-sitios/astro-frontend/src/pages/stores.astro", void 0);

const $$file = "C:/Users/niko_/OneDrive/Desktop/cafe-sitios/astro-frontend/src/pages/stores.astro";
const $$url = "/stores";

const _page = /*#__PURE__*/Object.freeze(/*#__PURE__*/Object.defineProperty({
  __proto__: null,
  default: $$Stores,
  file: $$file,
  url: $$url
}, Symbol.toStringTag, { value: 'Module' }));

const page = () => _page;

export { page };
