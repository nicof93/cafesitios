export type FeedbackCategory =
  | 'reportar_precio'
  | 'tienda_faltante'
  | 'sugerencia_ui'
  | 'otro';

export interface FeedbackSubmission {
  categoria: FeedbackCategory;
  mensaje: string;
  producto_id?: number;
  tienda?: string;
  email_contacto?: string;
}

