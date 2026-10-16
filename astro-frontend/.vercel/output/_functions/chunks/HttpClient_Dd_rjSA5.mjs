import { E as Environment } from './Environment_B2N0afMc.mjs';

class AppError extends Error {
  constructor(message, code = "APP_ERROR") {
    super(message);
    this.code = code;
    this.name = "AppError";
  }
}
class ApiError extends AppError {
  constructor(message, status, code = "API_ERROR") {
    super(message, code);
    this.status = status;
    this.name = "ApiError";
  }
}
class RateLimitError extends AppError {
  constructor(message = "Has superado el límite de solicitudes. Intenta más tarde.") {
    super(message, "RATE_LIMIT");
    this.name = "RateLimitError";
  }
}

class HttpClient {
  baseUrl;
  constructor(baseUrl) {
    this.baseUrl = baseUrl || Environment.getApiBaseUrl();
  }
  async get(path, options = {}) {
    return this.request(path, { ...options, method: "GET" });
  }
  async post(path, body, options = {}) {
    const headers = new Headers(options.headers || {});
    if (!headers.has("Content-Type")) {
      headers.set("Content-Type", "application/json");
    }
    return this.request(path, {
      ...options,
      method: "POST",
      headers,
      body: body ? JSON.stringify(body) : void 0
    });
  }
  async request(path, options) {
    const url = new URL(path.startsWith("http") ? path : `${this.baseUrl}${path.startsWith("/") ? "" : "/"}${path}`);
    if (options.params) {
      Object.entries(options.params).forEach(([key, value]) => {
        if (value !== void 0 && value !== null && value !== "") {
          url.searchParams.set(key, String(value));
        }
      });
    }
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), options.timeoutMs || 1e4);
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
        }
        throw new ApiError(errorMsg, response.status);
      }
      return await response.json();
    } catch (err) {
      if (err instanceof ApiError || err instanceof RateLimitError) {
        throw err;
      }
      if (err instanceof Error && err.name === "AbortError") {
        throw new ApiError("Tiempo de espera agotado al conectar con el servidor", 408);
      }
      throw new ApiError(err instanceof Error ? err.message : "Error de red desconocido", 500);
    } finally {
      clearTimeout(timeout);
    }
  }
}

export { HttpClient as H };
