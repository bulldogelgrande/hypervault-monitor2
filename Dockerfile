FROM mcr.microsoft.com/playwright/python:v1.43.0-jammy

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY scrape_hypervault.py .
CMD ["python", "scrape_hypervault.py"]

