import type { APIRoute } from 'astro';
import { HttpClient } from '../../../core/infrastructure/api/HttpClient';

export const GET: APIRoute = async ({ url }) => {
  try {
    const http = new HttpClient();
    const queryParams: Record<string, string> = {};

    url.searchParams.forEach((val, key) => {
      if (val !== undefined && val !== null && val !== '') {
        if (queryParams[key]) {
          queryParams[key] = `${queryParams[key]},${val}`;
        } else {
          queryParams[key] = val;
        }
      }
    });

    // Delegamos la consulta a la API de backend (FastAPI) a través de HttpClient
    const response: any = await http.get('/api/v1/products', {
      params: queryParams
    });

    if (response && Array.isArray(response.data)) {
      response.data = response.data.filter((p: any) => !p.oculto_catalogo);
    }

    return new Response(JSON.stringify(response), {
      status: 200,
      headers: {
        'Content-Type': 'application/json',
        'Cache-Control': 'public, s-maxage=60, stale-while-revalidate=300'
      }
    });
  } catch (error: any) {
    console.error('Error en API route Astro /api/v1/products:', error);
    return new Response(
      JSON.stringify({
        data: [],
        total_items: 0,
        error: error?.message || 'Error al consultar catálogo de productos'
      }),
      {
        status: error?.status || 500,
        headers: {
          'Content-Type': 'application/json'
        }
      }
    );
  }
};

