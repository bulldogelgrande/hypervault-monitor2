from datetime import datetime, timezone
from playwright.sync_api import sync_playwright, TimeoutError
# ... (resto de imports y helpers)

def obtener_capacidad_usdt0():
    """Devuelve usado, total y restante de USDT0; si no encuentra la fila, devuelve 0s."""
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        page = browser.new_page(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        # Carga la página y espera a que no haya peticiones de red
        page.goto("https://app.hypervault.finance/#/earn", wait_until="networkidle")
        # Espera adicional para que React pueble la tabla
        page.wait_for_timeout(10_000)

        try:
            # Busca una fila con una celda que contenga 'USDT0'
            fila = page.locator("//tr[./td[contains(., 'USDT0')]]").first
            # Espera a que sea visible hasta 60 segundos
            fila.wait_for(state="visible", timeout=60_000)
            # Asegura que la fila esté en pantalla
            fila.scroll_into_view_if_needed()
        except TimeoutError:
            print("No se encontró la fila de USDT0; se asume capacidad restante = 0")
            return 0.0, 0.0, 0.0

        # Extrae el texto de la última celda (ej. '1M / 1M')
        celdas = fila.locator("td")
        capacidad_texto = celdas.nth(celdas.count() - 1).inner_text().strip()
        usado_str, total_str = [s.strip() for s in capacidad_texto.split("/")]
        usado  = convertir_num(usado_str)
        total  = convertir_num(total_str)
        restante = max(total - usado, 0.0)
        return usado, total, restante

def run():
    usado, total, restante = obtener_capacidad_usdt0()
    ts = datetime.now(timezone.utc).isoformat()
    if restante < THRESHOLD:
        enviar_alerta(restante, usado, total, ts)
    else:
        print(f"{ts}: Capacidad OK ({restante} restante de {total})")

if __name__ == "__main__":
    run()
