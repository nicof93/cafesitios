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
  /**
   * Feature Flag: Preparador de pedidos por WhatsApp y carrito interactivo
   * Controlado por PUBLIC_ENABLE_WHATSAPP_ORDERS o ENABLE_WHATSAPP_ORDERS
   */
  static isWhatsAppOrdersEnabled(): boolean {
    const val = import.meta.env.PUBLIC_ENABLE_WHATSAPP_ORDERS ?? import.meta.env.ENABLE_WHATSAPP_ORDERS;
    return this.parseFlag(val, true);
  }

  /**
   * Feature Flag: Glosario de Café de Especialidad (/glosario)
   * Controlado por PUBLIC_ENABLE_GLOSSARY o ENABLE_GLOSSARY
   */
  static isGlossaryEnabled(): boolean {
    const val = import.meta.env.PUBLIC_ENABLE_GLOSSARY ?? import.meta.env.ENABLE_GLOSSARY;
    return this.parseFlag(val, true);
  }

  /**
   * Feature Flag: Chatbot Sommelier Digital de Café
   * Controlado por PUBLIC_ENABLE_CHATBOT_SOMMELIER o ENABLE_CHATBOT_SOMMELIER
   */
  static isChatbotSommelierEnabled(): boolean {
    const val = import.meta.env.PUBLIC_ENABLE_CHATBOT_SOMMELIER ?? import.meta.env.ENABLE_CHATBOT_SOMMELIER;
    return this.parseFlag(val, true);
  }

  static getAll(): Record<string, boolean> {
    return {
      guides: this.isGuidesEnabled(),
      calibrator: this.isCalibratorEnabled(),
      myRecipes: this.isMyRecipesEnabled(),
      flavorQuiz: this.isFlavorQuizEnabled(),
      whatsAppOrders: this.isWhatsAppOrdersEnabled(),
      glossary: this.isGlossaryEnabled(),
      chatbotSommelier: this.isChatbotSommelierEnabled(),
    };
  }
}

