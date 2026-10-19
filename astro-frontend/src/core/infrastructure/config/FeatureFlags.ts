/**
 * Sistema centralizado de Feature Flags para Cafesitios.
 *
 * Lee las variables de entorno de Astro / Vite (`import.meta.env`).
 * Las variables con prefijo `PUBLIC_` están disponibles tanto en SSR como en el cliente.
 * Si no se define una variable, se toma su valor por defecto (default true).
 */
export class FeatureFlags {
  private static parseFlag(value: any, defaultValue: boolean = true): boolean {
    if (value === undefined || value === null || value === '') {
      return defaultValue;
    }
    const str = String(value).trim().toLowerCase();
    return str === 'true' || str === '1' || str === 'yes' || str === 'on';
  }

  /**
   * Feature Flag: Guías de preparación de café de especialidad (/recetas)
   * Controlado por PUBLIC_ENABLE_RECIPES o ENABLE_RECIPES
   */
  static isGuidesEnabled(): boolean {
    const val = import.meta.env.PUBLIC_ENABLE_RECIPES ?? import.meta.env.ENABLE_RECIPES;
    return this.parseFlag(val, true);
  }

  /**
   * Feature Flag: Calibrador Sensorial 2D Dial-in Assistant (/calibrador)
   * Controlado por PUBLIC_ENABLE_CALIBRATOR o ENABLE_CALIBRATOR
   */
  static isCalibratorEnabled(): boolean {
    const val = import.meta.env.PUBLIC_ENABLE_CALIBRATOR ?? import.meta.env.ENABLE_CALIBRATOR;
    return this.parseFlag(val, true);
  }

  /**
   * Feature Flag: Mis Recetas / Bitácora Barista (/mis-recetas)
   * Controlado por PUBLIC_ENABLE_MY_RECIPES o ENABLE_MY_RECIPES
   */
  static isMyRecipesEnabled(): boolean {
    const val = import.meta.env.PUBLIC_ENABLE_MY_RECIPES ?? import.meta.env.ENABLE_MY_RECIPES;
    return this.parseFlag(val, true);
  }

  /**
   * Feature Flag: Quiz Interactivo de Sabor
   * Controlado por PUBLIC_ENABLE_FLAVOR_QUIZ o ENABLE_FLAVOR_QUIZ
   */
  static isFlavorQuizEnabled(): boolean {
    const val = import.meta.env.PUBLIC_ENABLE_FLAVOR_QUIZ ?? import.meta.env.ENABLE_FLAVOR_QUIZ;
    return this.parseFlag(val, true);
  }

  /**
   * Snapshot con todos los flags activos para telemetría o renderizado condicional en UI
   */
  static getAll(): Record<string, boolean> {
    return {
      guides: this.isGuidesEnabled(),
      calibrator: this.isCalibratorEnabled(),
      myRecipes: this.isMyRecipesEnabled(),
      flavorQuiz: this.isFlavorQuizEnabled(),
    };
  }
}

