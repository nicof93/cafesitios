export class Environment {
  static getApiBaseUrl(): string {
    // 1. En el navegador
    if (typeof window !== 'undefined') {
      const publicUrl = import.meta.env.PUBLIC_API_BASE_URL;
      if (publicUrl && typeof publicUrl === 'string' && publicUrl.trim()) {
        return publicUrl.replace(/\/+$/, '');
      }
      const isLocal = ['localhost', '127.0.0.1'].includes(window.location.hostname);
      return isLocal ? 'http://localhost:8000' : window.location.origin;
    }

    // 2. En el servidor (SSR / Vercel Edge / Node)
    const serverUrl = import.meta.env.INTERNAL_API_BASE_URL || import.meta.env.PUBLIC_API_BASE_URL;
    if (serverUrl && typeof serverUrl === 'string' && serverUrl.trim()) {
      return serverUrl.replace(/\/+$/, '');
    }

    return 'http://localhost:8000';
  }

  static getGtmId(): string {
    return import.meta.env.PUBLIC_GTM_ID || '';
  }

  static getGaMeasurementId(): string {
    return import.meta.env.PUBLIC_GA_MEASUREMENT_ID || '';
  }
}

