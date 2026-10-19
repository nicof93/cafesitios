export class AppError extends Error {
  constructor(message: string, public readonly code: string = 'APP_ERROR') {
    super(message);
    this.name = 'AppError';
  }
}

export class ApiError extends AppError {
  constructor(message: string, public readonly status: number, code: string = 'API_ERROR') {
    super(message, code);
    this.name = 'ApiError';
  }
}

export class NotFoundError extends AppError {
  constructor(entity: string, id: string | number) {
    super(`${entity} con id ${id} no fue encontrado`, 'NOT_FOUND');
    this.name = 'NotFoundError';
  }
}

export class RateLimitError extends AppError {
  constructor(message: string = 'Has superado el límite de solicitudes. Intenta más tarde.') {
    super(message, 'RATE_LIMIT');
    this.name = 'RateLimitError';
  }
}

