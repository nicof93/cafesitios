import { Recipe, type RecipeProps } from '../domain/models/Recipe';
import { HttpClient } from '../infrastructure/api/HttpClient';
import { LocalStorageAdapter } from '../infrastructure/storage/LocalStorageAdapter';

export class ManageRecipesUseCase {
  constructor(private readonly http: HttpClient = new HttpClient()) {}

  getLocalRecipes(): Recipe[] {
    return LocalStorageAdapter.getRecipes();
  }

  saveLocalRecipe(props: RecipeProps): Recipe[] {
    const recipe = new Recipe(props);
    return LocalStorageAdapter.saveRecipe(recipe);
  }

  deleteLocalRecipe(id: string): Recipe[] {
    return LocalStorageAdapter.deleteRecipe(id);
  }

  async syncToCloud(): Promise<{ success: boolean; message: string; count: number }> {
    const recipes = this.getLocalRecipes();
    if (recipes.length === 0) {
      return { success: false, message: 'No hay recetas para respaldar', count: 0 };
    }

    const deviceId = LocalStorageAdapter.getDeviceId();
    const latest = recipes[0];

    const payload = {
      device_id: deviceId,
      nombre_cafe: latest.cafe,
      metodo: latest.metodo,
      gramos_cafe: latest.gramos_cafe,
      gramos_agua: latest.gramos_agua,
      tiempo_segundos: 180,
      molienda: latest.molienda || 'Media',
      notas: latest.notas || 'Bitácora Astro',
      calificacion: latest.calificacion || 5,
      catacion_sca: latest.catacion_sca,
      puntuacion_sca_total: latest.puntuacion_sca_total
    };

    await this.http.post('/api/v1/recetas', payload);
    return {
      success: true,
      message: '¡Recetas respaldadas exitosamente en la nube!',
      count: recipes.length
    };
  }
}

