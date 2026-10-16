import { e as createComponent, k as renderComponent, r as renderTemplate, m as maybeRenderHead } from '../chunks/astro/server_D990-clo.mjs';
import 'piccolore';
import { $ as $$BaseLayout } from '../chunks/BaseLayout_BWXSiVi2.mjs';
export { renderers } from '../renderers.mjs';

const $$404 = createComponent(($$result, $$props, $$slots) => {
  return renderTemplate`${renderComponent($$result, "BaseLayout", $$BaseLayout, { "title": "P\xE1gina no encontrada | Cafe-sitios" }, { "default": ($$result2) => renderTemplate` ${maybeRenderHead()}<div class="py-20 text-center max-w-md mx-auto space-y-4"> <span class="text-5xl block">☕💨</span> <h1 class="text-2xl font-extrabold text-slate-800">404 - Café no encontrado</h1> <p class="text-xs text-slate-500">
El café o página que buscas puede haberse agotado, cambiado de enlace o ya no estar disponible.
</p> <div class="pt-4"> <a href="/" class="inline-block bg-emerald-800 hover:bg-emerald-900 text-white font-semibold text-xs px-5 py-3 rounded-2xl shadow transition">
Volver al catálogo principal
</a> </div> </div> ` })}`;
}, "C:/Users/niko_/OneDrive/Desktop/cafe-sitios/astro-frontend/src/pages/404.astro", void 0);

const $$file = "C:/Users/niko_/OneDrive/Desktop/cafe-sitios/astro-frontend/src/pages/404.astro";
const $$url = "/404";

const _page = /*#__PURE__*/Object.freeze(/*#__PURE__*/Object.defineProperty({
  __proto__: null,
  default: $$404,
  file: $$file,
  url: $$url
}, Symbol.toStringTag, { value: 'Module' }));

const page = () => _page;

export { page };
