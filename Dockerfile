# Usa la imagen oficial de Playwright para Python con todas las dependencias y navegadores
FROM mcr.microsoft.complaywrightpythonv1.43.0-jammy

# Prepara el directorio de trabajo
WORKDIR app

# Copia e instala dependencias de Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia el script de scraping
COPY scrape_hypervault.py .

# Comando por defecto ejecuta el script
CMD [python, scrape_hypervault.py]
