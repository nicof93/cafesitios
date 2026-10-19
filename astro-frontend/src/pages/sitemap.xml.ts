import type { APIRoute } from 'astro';
import { HttpClient } from '../core/infrastructure/api/HttpClient';

interface RawProduct {
  id: number;
  nombre: string;
  tienda?: string;
  imagen?: string | null;
  categoria?: string;
}

interface CatalogApiResponse {
  data: RawProduct[];
  total_items: number;
}

interface SyncLastResponse {
  last_sync?: string | null;
}

function escapeXml(unsafe: string): string {
  return unsafe.replace(/[<>&'"]/g, (c) => {
    switch (c) {
      case '<': return '&lt;';
      case '>': return '&gt;';
      case '&': return '&amp;';
      case '\'': return '&apos;';
      case '"': return '&quot;';
      default: return c;
    }
  });
}

function formatDate(dateStr?: string | null): string {
  if (!dateStr) return new Date().toISOString().split('T')[0];
  try {
    const d = new Date(dateStr);
    if (isNaN(d.getTime())) return new Date().toISOString().split('T')[0];
    return d.toISOString().split('T')[0];
  } catch {
    return new Date().toISOString().split('T')[0];
  }
}

export const GET: APIRoute = async () => {
  const siteUrl = 'https://cafesitios.cl';
  const today = new Date().toISOString().split('T')[0];
  const http = new HttpClient();

  let products: RawProduct[] = [];
  let lastSyncDate = today;

  try {
    // 1. Obtener última fecha de sincronización del scraper
    const syncRes = await http.get<SyncLastResponse>('/api/v1/sync/last').catch(() => null);
    if (syncRes?.last_sync) {
      lastSyncDate = formatDate(syncRes.last_sync);
    }

    // 2. Obtener lista de cafés activos del catálogo
    const catalogRes = await http.get<CatalogApiResponse>('/api/v1/products', {
      params: {
        limit: 1000,
        category: 'cafe',
        only_available: true,
        sort_by: 'created_desc'
      }
    }).catch(() => null);

    if (catalogRes?.data && Array.isArray(catalogRes.data)) {
      products = catalogRes.data;
    }
  } catch (err) {
    console.warn('[sitemap.xml] Error consultando API de productos para el sitemap:', err);
  }

  // 3. Páginas públicas estáticas canónicas
  const staticPages = [
    {
      loc: `${siteUrl}/`,
      lastmod: today,
      changefreq: 'daily',
      priority: '1.0'
    },
    {
      loc: `${siteUrl}/catalogo`,
      lastmod: today,
      changefreq: 'daily',
      priority: '0.9'
    },
    {
      loc: `${siteUrl}/tiendas`,
      lastmod: today,
      changefreq: 'weekly',
      priority: '0.8'
    },
    {
      loc: `${siteUrl}/recetas`,
      lastmod: today,
      changefreq: 'weekly',
      priority: '0.8'
    },
    {
      loc: `${siteUrl}/calibrador`,
      lastmod: today,
      changefreq: 'weekly',
      priority: '0.8'
    },
    {
      loc: `${siteUrl}/mis-recetas`,
      lastmod: today,
      changefreq: 'weekly',
      priority: '0.8'
    }
  ];

  // 4. Construcción del XML conforme a los estándares de Google Search Console
  const xml = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"
        xmlns:image="http://www.google.com/schemas/sitemap-image/1.1"
        xmlns:news="http://www.google.com/schemas/sitemap-news/0.9"
        xmlns:xhtml="http://www.w3.org/1999/xhtml">
${staticPages
  .map(
    (page) => `  <url>
    <loc>${escapeXml(page.loc)}</loc>
    <lastmod>${page.lastmod}</lastmod>
    <changefreq>${page.changefreq}</changefreq>
    <priority>${page.priority}</priority>
  </url>`
  )
  .join('\n')}
${products
  .map((product) => {
    const productUrl = `${siteUrl}/producto/${product.id}`;
    const imageTag = product.imagen
      ? `\n    <image:image>
      <image:loc>${escapeXml(product.imagen)}</image:loc>
      <image:title>${escapeXml(product.nombre || 'Café de especialidad')}</image:title>
    </image:image>`
      : '';

    return `  <url>
    <loc>${escapeXml(productUrl)}</loc>
    <lastmod>${lastSyncDate}</lastmod>
    <changefreq>weekly</changefreq>
    <priority>0.8</priority>${imageTag}
  </url>`;
  })
  .join('\n')}
</urlset>`;

  return new Response(xml.trim(), {
    status: 200,
    headers: {
      'Content-Type': 'application/xml; charset=utf-8',
      'Cache-Control': 'public, max-age=3600, s-maxage=86400, stale-while-revalidate=600',
      'X-Robots-Tag': 'noindex'
    }
  });
};
