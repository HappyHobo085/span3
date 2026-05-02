# Gebruik die amptelike ligte Python-beeld
FROM python:3.12-slim

# Stel die werksgids binne die houer
WORKDIR /app

# Installeer stelselafhanklikhede vir psycopg2
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Kopieer requirements eerste om Docker-cache te benut
COPY requirements.txt .

# Installeer Python-pakkette
RUN pip install --no-cache-dir -r requirements.txt

# Kopieer die res van die kode
COPY . .

# Stel die poort waarop FastAPI sal loop
EXPOSE 8000

# Begin die toepassing met uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
