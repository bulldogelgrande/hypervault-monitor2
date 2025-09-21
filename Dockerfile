FROM mcr.microsoft.com/playwright/python:v1.43.0-jammy

# Establece el directorio de trabajo dentro del contenedor
WORKDIR /app

# Copia e instala las dependencias de Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia el script de scraping al contenedor
COPY scrape_hype.py .

# Comando por defecto para ejecutar el scraper
CMD ["python", "scrape_hype.py"]