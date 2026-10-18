import type { CoffeeProduct } from './CoffeeProduct';

export type BrewMethod = 'espresso' | 'filtrado' | 'prensa' | 'cold_brew';
export type SensoryProfile = 'frutal_floral' | 'chocolate_nueces' | 'citrico_balanceado' | 'especiado_intenso';
export type AcidityPreference = 'baja' | 'media' | 'alta';

export interface QuizAnswers {
  metodo: BrewMethod;
  perfil: SensoryProfile;
  acidez: AcidityPreference;
}

export interface RecommendationItem {
  id: number;
  nombre: string;
  tienda: string;
  url_detalle: string;
  imagen?: string;
  proceso?: string;
  pais_origen?: string;
  variedad?: string;
  tueste?: string;
  precio_clp?: number;
  precio_por_kilo?: number;
  formato_gramos?: number;
  match_score?: number;
  puntaje_coincidencia?: number;
  motivo_recomendacion?: string;
  reasons?: string[];
  notas_cata?: string[];
  variante?: {
    precio_clp: number;
    precio_por_kilo: number;
    formato_gramos: number;
    disponible?: boolean;
    es_estimado?: boolean;
  };
}

