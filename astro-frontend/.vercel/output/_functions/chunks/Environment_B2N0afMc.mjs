class Environment {
  static getApiBaseUrl() {
    if (typeof window !== "undefined") {
      const publicUrl = "https://cafe-sitios.onrender.com";
      if (publicUrl.trim()) {
        return publicUrl.replace(/\/+$/, "");
      }
      const isLocal = ["localhost", "127.0.0.1"].includes(window.location.hostname);
      return isLocal ? "http://localhost:8000" : window.location.origin;
    }
    const serverUrl = "https://cafe-sitios.onrender.com";
    if (serverUrl.trim()) {
      return serverUrl.replace(/\/+$/, "");
    }
    return "http://localhost:8000";
  }
  static getGtmId() {
    return "";
  }
  static getGaMeasurementId() {
    return "";
  }
}

export { Environment as E };
