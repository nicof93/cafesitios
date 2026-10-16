import { ApiError, RateLimitError } from '../../domain/errors/DomainErrors';
import { Environment } from '../config/Environment';

export interface RequestOptions extends RequestInit {
  timeoutMs?: number;
  params?: Record<string, string | number | boolean | undefined | null>;
}

export class HttpClient {
  private readonly baseUrl: string;

  constructor(baseUrl?: string) {
    this.baseUrl = baseUrl || Environment.getApiBaseUrl();
  }

  async get<T>(path: string, options: RequestOptions = {}): Promise<T> {
    return this.request<T>(path, { ...options, method: 'GET' });
  }

  async post<T>(path: string, body?: unknown, options: RequestOptions = {}): Promise<T> {
    const headers = new Headers(options.headers || {});
    if (!headers.has('Content-Type')) {
      headers.set('Content-Type', 'application/json');
    }

    return this.request<T>(path, {
      ...options,
      method: 'POST',
      headers,
      body: body ? JSON.stringify(body) : undefined
    });
  }

  private async request<T>(path: string, options: RequestOptions): Promise<T> {
    const url = new URL(path.startsWith('http') ? path : `${this.baseUrl}${path.startsWith('/') ? '' : '/'}${path}`);

    if (options.params) {
      Object.entries(options.params).forEach(([key, value]) => {
        if (value !== undefined && value !== null && value !== '') {
          url.searchParams.set(key, String(value));
        }
      });
    }

    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), options.timeoutMs || 10000);

    try {
      const response = await fetch(url.toString(), {
        ...options,
        signal: controller.signal
      });

      if (response.status === 429) {
        throw new RateLimitError();
      }

      if (!response.ok) {
        let errorMsg = `Error HTTP ${response.status}: ${response.statusText}`;
        try {
          const errorJson = await response.json();
          if (errorJson && (errorJson.detail || errorJson.message)) {
            errorMsg = errorJson.detail || errorJson.message;
          }
        } catch {
          // No era JSON
        }
        throw new ApiError(errorMsg, response.status);
      }

      return (await response.json()) as T;
    } catch (err: unknown) {
      if (err instanceof ApiError || err instanceof RateLimitError) {
        throw err;
      }
      if (err instanceof Error && err.name === 'AbortError') {
        throw new ApiError('Tiempo de espera agotado al conectar con el servidor', 408);
      }
      throw new ApiError(err instanceof Error ? err.message : 'Error de red desconocido', 500);
    } finally {
      clearTimeout(timeout);
    }
  }
}

