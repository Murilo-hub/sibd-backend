FROM python:3.12-slim

WORKDIR /app

# Dependências do sistema (necessárias para algumas libs Python)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Instala dependências Python primeiro (cache de camadas)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia código da aplicação
COPY . .

# Cria diretórios de dados
RUN mkdir -p data/uploads data/processed data/vector_store data/logs

EXPOSE 8000

# Railway injeta $PORT automaticamente; fallback para 8000 em dev
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
