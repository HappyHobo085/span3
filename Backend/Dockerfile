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

# Kopieer entrypoint
COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

EXPOSE 8000

CMD ["./entrypoint.sh"]
