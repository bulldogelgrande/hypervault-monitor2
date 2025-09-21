"""
Scraper de Hypervault para extraer la capacidad del vault HYPE.

Este script utiliza Playwright para navegar a la página de Hypervault,
busca la fila correspondiente al pool "HYPE" en la tabla de Earn y
extrae la capacidad actual (usado, total, restante). Si la capacidad
restante está por debajo de un umbral definido (2 millones), imprime
un mensaje de alerta con detalles. De lo contrario, registra que la
capacidad es suficiente.

El envío de correo electrónico está deshabilitado en esta versión.
Las credenciales SMTP se mantienen por compatibilidad, pero no se
utilizan.
"""

from datetime import datetime, timezone
from playwright.sync_api import sync_playwright, TimeoutError
import re

# Umbral de capacidad restante (2 millones)
THRESHOLD = 2_000_000

# Configuración del correo SMTP (no utilizada en esta versión)
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USER = "tu-correo@gmail.com"
SMTP_PASS = "contraseña_o_token_app"
EMAIL_TO = "destinatario@example.com"

def abreviar_numero(n: float) -> str:
    """
    Convierte un número a notación abreviada (K, M).

    1_000 -> '1.0K'
    1_000_000 -> '1.0M'
    Otros números se muestran sin decimales.
    """
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return f"{n:.0f}"

def convertir_num(s: str) -> float:
    """
    Convierte una cadena que puede incluir sufijos 'K' o 'M' en un número float.

    Elimina comas y saltos de línea; maneja valores como '18K', '1.2M' o '1000'.
    Devuelve 0.0 si no se puede convertir.
    """
    if not s:
        return 0.0
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

def obtener_capacidad_hype() -> tuple[float, float, float]:
    """
    Navega a Hypervault y extrae la capacidad del vault HYPE.

    Devuelve una tupla (usado, total, restante). Si no encuentra la fila o
    los datos, devuelve ceros.
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        page = browser.new_page(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        )
        # Carga la página de Earn y espera hasta que no haya peticiones de red.
        page.goto("https://app.hypervault.finance/#/earn", wait_until="networkidle")
        # Espera extra para que la tabla se pueble
        page.wait_for_timeout(10_000)

        try:
            # Selecciona la fila que contenga 'HYPE'
            fila = page.locator("//tr[./td[contains(., 'HYPE')]]").first
            fila.wait_for(state="visible", timeout=60_000)
            fila.scroll_into_view_if_needed()
        except TimeoutError:
            print("No se encontró la fila de HYPE; se asume capacidad restante = 0")
            return 0.0, 0.0, 0.0

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
            print("No se pudo extraer el texto de la capacidad de HYPE.")
            return 0.0, 0.0, 0.0

        # Usa una expresión regular para extraer todas las secuencias numéricas con sufijo K o M
        # Esto permite capturar '19K', '30K' o '1.2M' aunque no haya barra separadora
        coincidencias = re.findall(r"\d+(?:\.\d+)?(?:[MK])?", capacidad_texto.upper())
        if len(coincidencias) >= 2:
            usado_str, total_str = coincidencias[0], coincidencias[1]
        elif len(coincidencias) == 1:
            # si sólo hay un número, asumimos que usado = total
            usado_str = total_str = coincidencias[0]
        else:
            return 0.0, 0.0, 0.0

        usado = convertir_num(usado_str)
        total = convertir_num(total_str)
        restante = max(total - usado, 0.0)
        return usado, total, restante

def enviar_alerta(restante: float, usado: float, total: float, ts: str) -> None:
    """
    Imprime un mensaje de alerta cuando la capacidad de HYPE es inferior al umbral.
    """
    mensaje = (
        "⚠️ Alerta: Capacidad de HYPE inferior a 2M\n\n"
        f"• Capacity restante: {restante:.0f} ({abreviar_numero(restante)})\n"
        f"• Capacidad usada: {usado:.0f} ({abreviar_numero(usado)})\n"
        f"• Capacidad total: {total:.0f} ({abreviar_numero(total)})\n"
        f"• Timestamp (UTC): {ts}\n"
        "• Fuente: app.hypervault.finance/#/earn\n"
        "• Enlace: https://app.hypervault.finance/#/earn\n"
    )
    print(mensaje)

def run() -> None:
    """
    Ejecuta la consulta de capacidad y decide si imprimir una alerta.
    """
    usado, total, restante = obtener_capacidad_hype()
    ts = datetime.now(timezone.utc).isoformat()
    if restante < THRESHOLD:
        enviar_alerta(restante, usado, total, ts)
    else:
        print(
            f"{ts}: Capacidad de HYPE OK ({abreviar_numero(restante)} restante de {abreviar_numero(total)})"
        )

if __name__ == "__main__":
    run()