import type { FeedbackSubmission } from '../domain/models/Feedback';
import { HttpClient } from '../infrastructure/api/HttpClient';

export class SubmitFeedbackUseCase {
  constructor(private readonly http: HttpClient = new HttpClient()) {}

  async execute(submission: FeedbackSubmission): Promise<{ success: boolean; message: string }> {
    await this.http.post('/api/v1/feedback', submission);
    return {
      success: true,
      message: '¡Muchas gracias! Tu sugerencia fue recibida.'
    };
  }
}

