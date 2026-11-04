import logging
import os
import smtplib
from email.message import EmailMessage
from typing import Optional

logger = logging.getLogger(__name__)


class EmailService:
    """
    Servicio de notificaciones por correo electrónico 100% gratuito utilizando
    exclusivamente la biblioteca estándar de Python (smtplib, email.message).
    
    Compatible con proveedores SMTP gratuitos (Gmail App Password, Brevo, Resend free, etc.).
    En modo desarrollo o sin credenciales, registra el correo en consola sin romper el flujo.
    """

    @classmethod
    def _get_config(cls):
        host = os.getenv("SMTP_HOST", "").strip()
        port = int(os.getenv("SMTP_PORT", "587"))
        user = os.getenv("SMTP_USER", "").strip()
        password = os.getenv("SMTP_PASSWORD", "").strip()
        from_email = os.getenv("SMTP_FROM", "Cafésitios <no-reply@cafesitios.cl>").strip()
        use_tls = os.getenv("SMTP_USE_TLS", "true").strip().lower() in ("true", "1", "yes")
        public_url = os.getenv("PUBLIC_APP_URL", "https://cafesitios.cl").rstrip("/")
        return {
            "host": host,
            "port": port,
            "user": user,
            "password": password,
            "from_email": from_email,
            "use_tls": use_tls,
            "public_url": public_url,
        }

    @classmethod
    def send_email(cls, to_email: str, subject: str, text_content: str, html_content: str) -> bool:
        config = cls._get_config()
        to_email = to_email.strip()

        if not to_email:
            logger.warning("[EMAIL] Intento de envío a dirección vacía.")
            return False

        # Si no hay servidor SMTP configurado, modo mock para desarrollo y testing
        if not config["host"]:
            logger.info(
                f"[EMAIL_MOCK] 📧 Correo simulado a <{to_email}>\n"
                f"Asunto: {subject}\n"
                f"Contenido Texto:\n{text_content}\n"
            )
            return True

        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = config["from_email"]
        msg["To"] = to_email
        msg.set_content(text_content)
        msg.add_alternative(html_content, subtype="html")

        try:
            if config["port"] == 465:
                # SSL directo
                with smtplib.SMTP_SSL(config["host"], config["port"], timeout=10) as server:
                    if config["user"] and config["password"]:
                        server.login(config["user"], config["password"])
                    server.send_message(msg)
            else:
                # STARTTLS (587 o estándar)
                with smtplib.SMTP(config["host"], config["port"], timeout=10) as server:
                    if config["use_tls"]:
                        server.starttls()
                    if config["user"] and config["password"]:
                        server.login(config["user"], config["password"])
                    server.send_message(msg)

            logger.info(f"[EMAIL] Correo enviado exitosamente a {to_email} (Asunto: {subject})")
            return True
        except Exception as e:
            logger.error(f"[EMAIL_ERROR] Falló el envío de correo a {to_email}: {e}")
            return False

    @classmethod
    def send_welcome_email(cls, to_email: str, tienda_nombre: str, login_url: Optional[str] = None) -> bool:
        config = cls._get_config()
        app_url = config["public_url"]
        target_login = login_url or f"{app_url}/admin-tienda/login"

        subject = f"☕ ¡Felicitaciones y bienvenido a Cafésitios, {tienda_nombre}!"

        text_content = f"""¡Hola {tienda_nombre}!

Te damos una calurosa bienvenida a Cafésitios, el ecosistema y comparador de café de especialidad de Chile.

Nos emociona que tu tostaduría forme parte de esta comunidad. Ya puedes acceder a tu panel de administración:
{target_login}

Las 4 principales cosas que puedes hacer en Cafésitios:
1. 💬 Configurar tu WhatsApp Comercial: Recibe pedidos directamente armados sin comisiones por venta (0% comisiones).
2. 📦 Subir tus Cafés y Fotos HD: Gestiona orígenes, procesos, notas de cata y fotos con cuota inicial de 250 MB.
3. ☕ Publicar tus Recetas Oficiales: Enseña a tus clientes a extraer tu café en V60, Espresso, Aeropress o Prensa.
4. 📈 Radar de Demanda y Métricas: Descubre qué orígenes y perfiles sensoriales están buscando los amantes del café en Chile.

Si tienes dudas, nuestro equipo de soporte está siempre disponible para ayudarte.

¡Mucho éxito con tus tuestes!
El equipo de Cafésitios
{app_url}
"""

        html_content = f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <title>Bienvenido a Cafésitios</title>
</head>
<body style="margin: 0; padding: 0; background-color: #fafaf9; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #1c1917;">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background-color: #fafaf9; padding: 30px 10px;">
    <tr>
      <td align="center">
        <table role="presentation" width="100%" style="max-width: 600px; background-color: #ffffff; border-radius: 16px; border: 1px solid #e7e5e4; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);">
          <!-- Header -->
          <tr>
            <td style="background-color: #064e3b; padding: 32px 24px; text-align: center;">
              <span style="font-size: 40px; display: inline-block; margin-bottom: 8px;">☕</span>
              <h1 style="color: #ffffff; font-size: 24px; font-weight: 800; margin: 0; letter-spacing: -0.5px;">¡Bienvenido a Cafésitios!</h1>
              <p style="color: #a7f3d0; font-size: 14px; margin: 6px 0 0 0; font-weight: 500;">El primer ecosistema de café de especialidad en Chile</p>
            </td>
          </tr>

          <!-- Cuerpo -->
          <tr>
            <td style="padding: 32px 28px;">
              <p style="font-size: 16px; line-height: 1.5; color: #1c1917; margin: 0 0 16px 0;">
                ¡Hola equipo de <strong>{tienda_nombre}</strong>!
              </p>
              <p style="font-size: 14px; line-height: 1.6; color: #44403c; margin: 0 0 24px 0;">
                Te felicitamos y agradecemos por sumarte a Cafésitios. Nuestro propósito es conectar el valor artesanal de tu tostaduría directamente con consumidores educados que buscan café de origen y calidad, <strong>sin comisiones intermedias por venta</strong>.
              </p>

              <!-- Botón CTA -->
              <div style="text-align: center; margin: 28px 0;">
                <a href="{target_login}" style="background-color: #047857; color: #ffffff; text-decoration: none; font-weight: 700; font-size: 14px; padding: 14px 28px; border-radius: 12px; display: inline-block; box-shadow: 0 2px 4px rgba(4, 120, 87, 0.2);">
                  Ir a mi Panel de Tostaduría ➔
                </a>
              </div>

              <!-- 4 Acciones Clave -->
              <div style="background-color: #f5f5f4; border-radius: 12px; padding: 20px; border: 1px solid #e7e5e4; margin: 24px 0;">
                <h3 style="font-size: 13px; font-weight: 800; text-transform: uppercase; color: #064e3b; margin: 0 0 14px 0; letter-spacing: 0.5px;">
                  🚀 4 Cosas clave que puedes hacer en tu panel:
                </h3>
                <ul style="margin: 0; padding-left: 18px; font-size: 13px; line-height: 1.7; color: #292524;">
                  <li><strong>💬 WhatsApp Comercial:</strong> Configura tu número para recibir pedidos armados con 0% de comisión.</li>
                  <li><strong>📦 Catálogo y Fotos HD:</strong> Muestra tus cafés, notas de cata y fotos con cuota de 250 MB.</li>
                  <li><strong>☕ Recetas Oficiales:</strong> Publica tus ratios y parámetros de extracción para tus clientes.</li>
                  <li><strong>📈 Radar de Demanda:</strong> Revisa qué orígenes y procesos busca el público en Chile.</li>
                </ul>
              </div>

              <p style="font-size: 12px; color: #78716c; line-height: 1.5; margin: 24px 0 0 0;">
                Si necesitas ayuda para sincronizar tu catálogo de Shopify o WooCommerce, estamos a un mensaje de distancia.
              </p>
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="background-color: #fafaf9; border-top: 1px solid #e7e5e4; padding: 20px 24px; text-align: center;">
              <p style="font-size: 12px; color: #a8a29e; margin: 0;">
                Cafésitios &bull; Comparador y Comunidad de Café de Especialidad en Chile<br>
                <a href="{app_url}" style="color: #047857; text-decoration: none; font-weight: 600;">cafesitios.cl</a>
              </p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>
"""
        return cls.send_email(to_email, subject, text_content, html_content)

    @classmethod
    def send_password_reset_email(cls, to_email: str, tienda_nombre: str, reset_url: str) -> bool:
        config = cls._get_config()
        app_url = config["public_url"]

        subject = "🔑 Restablecimiento de contraseña de tu cuenta en Cafésitios"

        text_content = f"""Hola {tienda_nombre},

Hemos recibido una solicitud para restablecer la contraseña de acceso a tu panel de administración en Cafésitios.

Para definir una nueva contraseña, haz clic en el siguiente enlace (válido por 2 horas):
{reset_url}

Si tú no solicitaste este cambio, puedes ignorar este correo; tu contraseña actual continuará siendo segura.

Atentamente,
El equipo de Cafésitios
{app_url}
"""

        html_content = f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <title>Restablecer Contraseña</title>
</head>
<body style="margin: 0; padding: 0; background-color: #fafaf9; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #1c1917;">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background-color: #fafaf9; padding: 30px 10px;">
    <tr>
      <td align="center">
        <table role="presentation" width="100%" style="max-width: 550px; background-color: #ffffff; border-radius: 16px; border: 1px solid #e7e5e4; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);">
          <tr>
            <td style="background-color: #1c1917; padding: 28px 24px; text-align: center;">
              <span style="font-size: 36px; display: inline-block; margin-bottom: 6px;">🔑</span>
              <h1 style="color: #ffffff; font-size: 20px; font-weight: 800; margin: 0;">Restablecer tu Contraseña</h1>
              <p style="color: #a8a29e; font-size: 13px; margin: 4px 0 0 0;">Panel de Tostaduría &bull; Cafésitios</p>
            </td>
          </tr>

          <tr>
            <td style="padding: 32px 28px;">
              <p style="font-size: 14px; line-height: 1.6; color: #1c1917; margin: 0 0 16px 0;">
                Hola <strong>{tienda_nombre}</strong>,
              </p>
              <p style="font-size: 14px; line-height: 1.6; color: #44403c; margin: 0 0 24px 0;">
                Recibimos una solicitud para restablecer la contraseña de acceso asociada a tu cuenta de administrador (<strong>{to_email}</strong>).
              </p>

              <div style="text-align: center; margin: 28px 0;">
                <a href="{reset_url}" style="background-color: #047857; color: #ffffff; text-decoration: none; font-weight: 700; font-size: 14px; padding: 13px 28px; border-radius: 12px; display: inline-block; box-shadow: 0 2px 4px rgba(4, 120, 87, 0.2);">
                  Definir Nueva Contraseña ➔
                </a>
              </div>

              <p style="font-size: 12px; line-height: 1.5; color: #78716c; margin: 20px 0 0 0;">
                Este enlace es de uso único y expirará en <strong>2 horas</strong> por motivos de seguridad.<br>
                Si el botón no funciona, copia y pega el siguiente enlace en tu navegador:<br>
                <a href="{reset_url}" style="color: #047857; word-break: break-all; font-size: 11px;">{reset_url}</a>
              </p>

              <hr style="border: none; border-top: 1px solid #f5f5f4; margin: 24px 0;">

              <p style="font-size: 11px; color: #a8a29e; line-height: 1.4; margin: 0;">
                🛡️ Si no solicitaste este cambio, no te preocupes: tu contraseña no ha sido modificada y puedes ignorar este mensaje con total tranquilidad.
              </p>
            </td>
          </tr>

          <tr>
            <td style="background-color: #fafaf9; border-top: 1px solid #e7e5e4; padding: 16px 24px; text-align: center;">
              <p style="font-size: 11px; color: #a8a29e; margin: 0;">
                Cafésitios &bull; <a href="{app_url}" style="color: #78716c; text-decoration: none;">cafesitios.cl</a>
              </p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>
"""
        return cls.send_email(to_email, subject, text_content, html_content)

