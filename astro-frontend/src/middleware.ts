import { defineMiddleware } from 'astro:middleware';

export const onRequest = defineMiddleware(async (context, next) => {
  const host = context.request.headers.get('host') || context.url.host || '';
  const pathname = context.url.pathname;

  // Detección de subdominio administrativo (admin.cafesitios.cl, admin.cafesitios.vercel.app, admin.localhost, etc.)
  const isAdminSubdomain = host.startsWith('admin.');

  if (isAdminSubdomain) {
    if (pathname === '/' || pathname === '') {
      return context.redirect('/admin-tienda/dashboard');
    }
    if (pathname === '/login') {
      return context.redirect('/admin-tienda/login');
    }
    if (pathname === '/dashboard') {
      return context.redirect('/admin-tienda/dashboard');
    }
    if (pathname === '/productos') {
      return context.redirect('/admin-tienda/productos');
    }
    if (pathname === '/auditoria') {
      return context.redirect('/admin-tienda/auditoria');
    }
  }

  return next();
});
