import type { QuizAnswers, RecommendationItem } from '../domain/models/Recommendation';
import { HttpClient } from '../infrastructure/api/HttpClient';

interface RawRecommendationsResponse {
  recomendaciones: RecommendationItem[];
  total: number;
}

export class GetRecommendationsUseCase {
  constructor(private readonly http: HttpClient = new HttpClient()) {}

  async execute(answers: QuizAnswers): Promise<RecommendationItem[]> {
    const response = await this.http.get<RawRecommendationsResponse>('/api/v1/products/recommend', {
      params: {
        metodo: answers.metodo,
        perfil: answers.perfil,
        acidez: answers.acidez
      }
    });

    return response.recomendaciones || [];
  }
}

