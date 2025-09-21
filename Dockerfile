FROM mcr.microsoft.com/playwright/python:v1.43.0-jammy

# Establece el directorio de trabajo dentro del contenedor
WORKDIR /app

# Copia e instala las dependencias de Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia el código de la aplicación y del scraper al contenedor
COPY . .

# Comando por defecto: levanta el servidor Flask
CMD ["python", "app.py"]