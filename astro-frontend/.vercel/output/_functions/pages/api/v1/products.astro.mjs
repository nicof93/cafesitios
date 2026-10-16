import { H as HttpClient } from '../../../chunks/HttpClient_Dd_rjSA5.mjs';
export { renderers } from '../../../renderers.mjs';

const GET = async ({ url }) => {
  try {
    const http = new HttpClient();
    const queryParams = {};
    url.searchParams.forEach((val, key) => {
      if (val !== void 0 && val !== null && val !== "") {
        queryParams[key] = val;
      }
    });
    const response = await http.get("/api/v1/products", {
      params: queryParams
    });
    return new Response(JSON.stringify(response), {
      status: 200,
      headers: {
        "Content-Type": "application/json",
        "Cache-Control": "public, max-age=60, s-maxage=300"
      }
    });
  } catch (error) {
    console.error("Error en API route Astro /api/v1/products:", error);
    return new Response(
      JSON.stringify({
        data: [],
        total_items: 0,
        error: error?.message || "Error al consultar catálogo de productos"
      }),
      {
        status: error?.status || 500,
        headers: {
          "Content-Type": "application/json"
        }
      }
    );
  }
};

const _page = /*#__PURE__*/Object.freeze(/*#__PURE__*/Object.defineProperty({
  __proto__: null,
  GET
}, Symbol.toStringTag, { value: 'Module' }));

const page = () => _page;

export { page };
