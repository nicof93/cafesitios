export class Environment {
  static getApiBaseUrl(): string {
    // 1. En el navegador
    if (typeof window !== 'undefined') {
      const publicUrl = import.meta.env.PUBLIC_API_BASE_URL;
      if (publicUrl && typeof publicUrl === 'string' && publicUrl.trim()) {
        return publicUrl.replace(/\/+$/, '');
      }
      const isLocal = ['localhost', '127.0.0.1'].includes(window.location.hostname);
      return isLocal ? `http://${window.location.hostname}:8000` : window.location.origin;
    }

    // 2. En el servidor (SSR / Vercel Edge / Node)
    const serverUrl = import.meta.env.INTERNAL_API_BASE_URL || import.meta.env.PUBLIC_API_BASE_URL;
    if (serverUrl && typeof serverUrl === 'string' && serverUrl.trim()) {
      return serverUrl.replace(/\/+$/, '');
    }

    return 'http://localhost:8000';
  }

  static isLocalhost(url?: URL | string): boolean {
    if (typeof window !== 'undefined') {
      const hostname = window.location.hostname.toLowerCase();
      return hostname === 'localhost' || hostname === '127.0.0.1' || hostname === '[::1]' || hostname.endsWith('.local');
    }
    if (url) {
      try {
        const u = typeof url === 'string' ? new URL(url) : url;
        const host = u.hostname.toLowerCase();
        return host === 'localhost' || host === '127.0.0.1' || host === '[::1]' || host.endsWith('.local');
      } catch {
        return false;
      }
    }
    const env = (import.meta.env.NODE_ENV || import.meta.env.MODE || '').toLowerCase();
    return env === 'development' || env === 'dev';
  }

  static isLocalAdminEnabled(url?: URL | string): boolean {
    const flag = import.meta.env.ENABLE_LOCAL_ADMIN;
    if (flag === 'false' || flag === '0') return false;
    return this.isLocalhost(url);
  }

  static isAnalyticsEnabled(url?: URL | string): boolean {
    const flag = import.meta.env.ENABLE_SYNC_ANALYTICS;
    if (flag === 'false' || flag === '0') return false;
    return this.isLocalhost(url);
  }

  static getGtmId(): string {
    return import.meta.env.PUBLIC_GTM_ID || '';
  }

  static getGaMeasurementId(): string {
    return import.meta.env.PUBLIC_GA_MEASUREMENT_ID || '';
  }
}

