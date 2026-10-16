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
  match_score: number;
  reasons?: string[];
  variante?: {
    precio_clp: number;
    precio_por_kilo: number;
    formato_gramos: number;
  };
}

