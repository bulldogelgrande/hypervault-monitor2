from datetime import datetime, timezone
from playwright.sync_api import sync_playwright
import smtplib
from email.mime.text import MIMEText

# Umbral de capacidad restante (2M)
THRESHOLD = 2_000_000

# Configura aquí tus credenciales SMTP y destinatario
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USER = "tu-correo@gmail.com"
SMTP_PASS = "contraseña_o_token_app"
EMAIL_TO   = "bulldog_32@hotmail.com"

def abreviar_numero(n: float) -> str:
    """Convierte un número en notación abreviada (K, M)."""
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}M"
    elif n >= 1_000:
        return f"{n/1_000:.1f}K"
    return str(n)

def convertir_num(s: str) -> float:
    """Convierte una cadena como '1M' o '97' en un número."""
    s = s.strip().upper()
    if s.endswith("M"):
        return float(s[:-1]) * 1_000_000
    if s.endswith("K"):
        return float(s[:-1]) * 1_000
    return float(s)

def obtener_capacidad_usdt0():
    """Devuelve (used, total, remaining) de la fila USDT0."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        # Carga la página y espera a que se estabilicen las peticiones
        page.goto("https://app.hypervault.finance/#/earn", wait_until="networkidle")
        # Espera a que aparezca la fila 'USDT0'
        fila = page.locator("tr:has-text('USDT0')")
        fila.wait_for(timeout=30000)
        # La última celda de la fila contiene algo como '1M / 1M'
        celdas = fila.locator("td")
        capacidad_texto = celdas.nth(celdas.count() - 1).inner_text().strip()
        usado_str, total_str = [x.strip() for x in capacidad_texto.split("/")]
        usado  = convertir_num(usado_str)
        total  = convertir_num(total_str)
        restante = max(total - usado, 0)
        return usado, total, restante

def enviar_alerta(restante: float, usado: float, total: float, ts: str):
    """Envia correo si la capacidad restante es inferior al umbral."""
    asunto = "Hypervault USDT Capacity < 2M"
    cuerpo  = (
        f"⚠️ Alerta: Capacidad de USDT0 inferior a 2M\n\n"
        f"• Capacity restante: {restante:.0f} ({abreviar_numero(restante)})\n"
        f"• Capacidad usada: {usado:.0f} ({abreviar_numero(usado)})\n"
        f"• Capacidad total: {total:.0f} ({abreviar_numero(total)})\n"
        f"• Timestamp: {ts}\n"
        f"• Fuente: app.hypervault.finance/#/earn\n"
        f"• Enlace: https://app.hypervault.finance/#/earn\n"
    )
    msg = MIMEText(cuerpo)
    msg["Subject"] = asunto
    msg["From"] = SMTP_USER
    msg["To"] = EMAIL_TO

    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.send_message(msg)

def run():
    usado, total, restante = obtener_capacidad_usdt0()
    ts = datetime.now(timezone.utc).isoformat()
    # Si la capacidad restante es inferior al umbral, envía alerta
    if restante < THRESHOLD:
        enviar_alerta(restante, usado, total, ts)
    else:
        # Solo se imprime, o puedes registrar en logs
        print(f"{ts}: Capacidad OK ({abreviar_numero(restante)} restante de {abreviar_numero(total)})")

if __name__ == "__main__":
    run()
