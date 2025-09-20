from datetime import datetime, timezone
from playwright.sync_api import sync_playwright, TimeoutError
import smtplib
from email.mime.text import MIMEText

# Umbral de capacidad restante (2 millones)
THRESHOLD = 2_000_000

# Configuración de correo saliente (ajusta con tus datos reales)
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USER = "tu-correo@gmail.com"
SMTP_PASS = "contraseña_o_token_app"
EMAIL_TO   = "bulldog_32@hotmail.com"

def abreviar_numero(n: float) -> str:
    """Convierte un número en notación abreviada (K, M)."""
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return f"{n:.0f}"

def convertir_num(s: str) -> float:
    """Convierte una cadena como '1M', '97K' o '123' en un número."""
    s = s.strip().upper()
    if s.endswith("M"):
        return float(s[:-1].replace(",", "")) * 1_000_000
    if s.endswith("K"):
        return float(s[:-1].replace(",", "")) * 1_000
    try:
        return float(s.replace(",", ""))
    except ValueError:
        return 0.0

def obtener_capacidad_usdt0() -> tuple[float, float, float]:
    """Navega hasta Hypervault y extrae (usado, total, restante) de la fila USDT0."""
    with sync_playwright() as p:
        # Lanza Chromium en modo headless con argumentos seguros
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        # Configura user agent para parecer un navegador real
        page = browser.new_page(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/120.0.0.0 Safari/537.36"
        )
        # Carga la página y espera a que las peticiones de red se estabilicen
        page.goto("https://app.hypervault.finance/#/earn", wait_until="networkidle")
        # Espera 10 segundos extra para que React pueble la tabla
        page.wait_for_timeout(10_000)

        try:
            # Selector robusto: fila cuyo td contiene 'USDT0'
            fila = page.locator("//tr[./td[contains(., 'USDT0')]]").first
            # Espera a que la fila esté visible (máximo 60 s)
            fila.wait_for(state="visible", timeout=60_000)
            # Asegura que la fila está en el viewport
            fila.scroll_into_view_if_needed()
        except TimeoutError:
            # Si no encuentra la fila, devuelve capacidad cero
            print("No se encontró la fila de USDT0; se asume capacidad restante = 0")
            return 0.0, 0.0, 0.0

        # Extrae la última celda (capacidad: usado / total)
        celdas = fila.locator("td")
        capacidad_texto = celdas.nth(celdas.count() - 1).inner_text().strip()
        # Separa por '/' y controla casos con un único valor
        cap_parts = [s.strip() for s in capacidad_texto.split("/")]
        if len(cap_parts) == 2:
            usado_str, total_str = cap_parts
        elif len(cap_parts) == 1 and cap_parts[0]:
            usado_str = cap_parts[0]
            total_str = cap_parts[0]  # si sólo hay un valor, asumimos usado = total
        else:
            usado_str = "0"
            total_str = "0"

        usado  = convertir_num(usado_str)
        total  = convertir_num(total_str)
        restante = max(total - usado, 0.0)
        return usado, total, restante

def enviar_alerta(restante: float, usado: float, total: float, ts: str) -> None:
    """Envía un correo de alerta cuando la capacidad restante es inferior al umbral."""
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
    msg = MIMEText(cuerpo)
    msg["Subject"] = asunto
    msg["From"] = SMTP_USER
    msg["To"] = EMAIL_TO

    # Envía el correo
    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.send_message(msg)

def run() -> None:
    """Ejecuta la verificación y envía alerta si procede."""
    usado, total, restante = obtener_capacidad_usdt0()
    ts = datetime.now(timezone.utc).isoformat()
    if restante < THRESHOLD:
        enviar_alerta(restante, usado, total, ts)
    else:
        # Para depuración: imprime en logs si no hay alerta
        print(f"{ts}: Capacidad OK ({abreviar_numero(restante)} restante de {abreviar_numero(total)})")

if __name__ == "__main__":
    run()
