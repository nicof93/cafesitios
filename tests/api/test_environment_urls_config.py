import unittest
from db.environments import EnvironmentManager


class TestEnvironmentUrlsConfig(unittest.TestCase):
    def test_get_urls_for_default_environments(self):
        # Supabase
        urls_sup = EnvironmentManager.get_urls_for_env("supabase")
        self.assertEqual(urls_sup.get("url_catalogo_base"), "https://cafesitios.cl")
        self.assertEqual(urls_sup.get("url_admin_tienda_base"), "https://cafesitios.cl")

        # Local
        urls_loc = EnvironmentManager.get_urls_for_env("local")
        self.assertEqual(urls_loc.get("url_catalogo_base"), "http://localhost:4321")
        self.assertEqual(urls_loc.get("url_admin_tienda_base"), "http://localhost:4321")

    def test_update_environment_custom_urls(self):
        # Crear ambiente temporal de prueba
        test_env_id = "test-custom-urls"
        EnvironmentManager.save_environment({
            "id": test_env_id,
            "nombre": "Staging Cloud",
            "connection_url": "sqlite:///:memory:",
            "url_catalogo_base": "https://staging.cafesitios.cl",
            "url_admin_tienda_base": "https://admin-staging.cafesitios.cl",
        })

        try:
            urls = EnvironmentManager.get_urls_for_env(test_env_id)
            self.assertEqual(urls["url_catalogo_base"], "https://staging.cafesitios.cl")
            self.assertEqual(urls["url_admin_tienda_base"], "https://admin-staging.cafesitios.cl")

            # Modificar solo la URL de admin
            EnvironmentManager.update_environment(test_env_id, {
                "url_admin_tienda_base": "https://portal.cafesitios.cl"
            })
            updated_urls = EnvironmentManager.get_urls_for_env(test_env_id)
            self.assertEqual(updated_urls["url_catalogo_base"], "https://staging.cafesitios.cl")
            self.assertEqual(updated_urls["url_admin_tienda_base"], "https://portal.cafesitios.cl")
        finally:
            EnvironmentManager.delete_environment(test_env_id)


if __name__ == "__main__":
    unittest.main()

