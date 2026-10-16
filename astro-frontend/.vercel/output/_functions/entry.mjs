import { renderers } from './renderers.mjs';
import { c as createExports, s as serverEntrypointModule } from './chunks/_@astrojs-ssr-adapter_DQfXNPnj.mjs';
import { manifest } from './manifest_CpUC-obK.mjs';

const serverIslandMap = new Map();;

const _page0 = () => import('./pages/_image.astro.mjs');
const _page1 = () => import('./pages/404.astro.mjs');
const _page2 = () => import('./pages/api/v1/products.astro.mjs');
const _page3 = () => import('./pages/bitacora.astro.mjs');
const _page4 = () => import('./pages/catalog.astro.mjs');
const _page5 = () => import('./pages/product/_id_.astro.mjs');
const _page6 = () => import('./pages/stores.astro.mjs');
const _page7 = () => import('./pages/index.astro.mjs');
const pageMap = new Map([
    ["node_modules/astro/dist/assets/endpoint/generic.js", _page0],
    ["src/pages/404.astro", _page1],
    ["src/pages/api/v1/products.ts", _page2],
    ["src/pages/bitacora.astro", _page3],
    ["src/pages/catalog.astro", _page4],
    ["src/pages/product/[id].astro", _page5],
    ["src/pages/stores.astro", _page6],
    ["src/pages/index.astro", _page7]
]);

const _manifest = Object.assign(manifest, {
    pageMap,
    serverIslandMap,
    renderers,
    actions: () => import('./noop-entrypoint.mjs'),
    middleware: () => import('./_noop-middleware.mjs')
});
const _args = {
    "middlewareSecret": "87cd2e07-d28a-42dc-a58e-e6ae4c1775bd",
    "skewProtection": false
};
const _exports = createExports(_manifest, _args);
const __astrojsSsrVirtualEntry = _exports.default;
const _start = 'start';
if (Object.prototype.hasOwnProperty.call(serverEntrypointModule, _start)) ;

export { __astrojsSsrVirtualEntry as default, pageMap };
