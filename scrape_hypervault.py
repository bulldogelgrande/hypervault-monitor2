from datetime import datetime, timezone
from playwright.sync_api import sync_playwright, TimeoutError
import smtplib
from email.mime.text import MIMEText

# Umbral de capacidad restante (2 millones).
THRESHOLD = 2_000_000

# Configuración del correo SMTP.
# Sustituye estas credenciales por las tuyas antes de usar el script.
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USER = "tu-correo@gmail.com"
SMTP_PASS = "contraseña_o_token_app"
EMAIL_TO = "bulldog_32@hotmail.com"

def abreviar_numero(n: float) -> str:
    """
    Convierte un número a una notación abreviada.

    1000 => '1.0K'
    1000000 => '1.0M'
    """
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return f"{n:.0f}"

def convertir_num(s: str) -> float:
    """
    Convierte una cadena que puede contener unidades 'K' o 'M' en un número flotante.

    Elimina comas y saltos de línea para manejar casos como '1M\n1' o '1,000'.
    Devuelve 0.0 en caso de error.
    """
    if not s:
        return 0.0
    # Limpia comas y saltos de línea, y normaliza a mayúsculas
    s_clean = s.replace(",", "").replace("\n", "").strip().upper()
    try:
        if s_clean.endswith("M"):
            return float(s_clean[:-1]) * 1_000_000
        elif s_clean.endswith("K"):
            return float(s_clean[:-1]) * 1_000
        else:
            return float(s_clean)
    except (ValueError, IndexError):
        return 0.0

def obtener_capacidad_usdt0() -> tuple[float, float, float]:
    """
    Navega hasta la página de Hypervault y extrae la capacidad usada, total
    y restante del pool USDT0.

    Si no se puede encontrar la fila o los datos, devuelve (0.0, 0.0, 0.0).
    """
    with sync_playwright() as p:
        # Lanza Chromium en modo headless.
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        # Crea una nueva página con un user-agent de navegador real.
        page = browser.new_page(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        )
        # Carga la página y espera a que no haya actividad de red.
        page.goto("https://app.hypervault.finance/#/earn", wait_until="networkidle")
        # Espera extra para que la tabla se pueble completamente.
        page.wait_for_timeout(10_000)

        try:
            # Selecciona la fila que contiene USDT0 en alguna de sus celdas.
            fila = page.locator("//tr[./td[contains(., 'USDT0')]]").first
            # Espera a que la fila sea visible.
            fila.wait_for(state="visible", timeout=60_000)
            # Asegura que la fila esté en el viewport.
            fila.scroll_into_view_if_needed()
        except TimeoutError:
            # Si no se encuentra la fila, se asume capacidad cero.
            print("No se encontró la fila de USDT0; se asume capacidad restante = 0")
            return 0.0, 0.0, 0.0

        # Obtiene todas las celdas de la fila y extrae la última, donde se muestran
        # los valores "usado/total" (p. ej., "1M / 1M").
        celdas = fila.locator("td")
        try:
            capacidad_texto = (
                celdas.nth(celdas.count() - 1)
                .inner_text()
                .replace("\n", "")
                .replace(",", "")
                .strip()
            )
        except Exception:
            print("No se pudo extraer el texto de la capacidad.")
            return 0.0, 0.0, 0.0

        # Divide la cadena en partes separadas por "/", eliminando espacios.
        cap_parts = [part.strip() for part in capacidad_texto.split("/") if part.strip()]
        if len(cap_parts) == 2:
            usado_str, total_str = cap_parts
        elif len(cap_parts) == 1:
            usado_str = total_str = cap_parts[0]
        else:
            # Si no hay valores legibles, devuelve ceros.
            return 0.0, 0.0, 0.0

        usado = convertir_num(usado_str)
        total = convertir_num(total_str)
        restante = max(total - usado, 0.0)
        return usado, total, restante

def enviar_alerta(restante: float, usado: float, total: float, ts: str) -> None:
    """
    Envía un correo de alerta si la capacidad restante es inferior al umbral.

    El asunto y cuerpo del correo incluyen los valores numéricos tanto en
    formato completo como abreviado.
    """
    asunto = "Hypervault USDT Capacity < 2M"
    cuerpo = (
        "⚠️ Alerta: Capacidad de USDT0 inferior a 2M\n\n"
        f"• Capacity restante: {restante:.0f} ({abreviar_numero(restante)})\n"
        f"• Capacidad usada: {usado:.0f} ({abreviar_numero(usado)})\n"
        f"• Capacidad total: {total:.0f} ({abreviar_numero(total)})\n"
        f"• Timestamp (UTC): {ts}\n"
        "• Fuente: app.hypervault.finance/#/earn\n"
        "• Enlace: https://app.hypervault.finance/#/earn\n"
    )
    # Construye el mensaje de correo.
    msg = MIMEText(cuerpo)
    msg["Subject"] = asunto
    msg["From"] = SMTP_USER
    msg["To"] = EMAIL_TO

    # Envía el correo usando SMTP.
    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.send_message(msg)

def run() -> None:
    """
    Ejecuta el chequeo de capacidad y envía alerta si procede.

    Si la capacidad restante es menor que el umbral, se envía correo; de lo contrario,
    se imprime un mensaje informativo en los logs.
    """
    usado, total, restante = obtener_capacidad_usdt0()
    ts = datetime.now(timezone.utc).isoformat()
    if restante < THRESHOLD:
        enviar_alerta(restante, usado, total, ts)
    else:
        print(
            f"{ts}: Capacidad OK ({abreviar_numero(restante)} restante de {abreviar_numero(total)})"
        )

if __name__ == "__main__":
    run()