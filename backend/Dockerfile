# Image backend El-Haress : sert a la fois l'API (uvicorn) et le collector.
# Le meme code, deux commandes differentes (voir docker-compose).
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Dependances d'abord : couche mise en cache tant que pyproject/src ne changent pas.
COPY pyproject.toml ./
COPY src ./src
RUN pip install -e .

# Migrations, utilitaires et point d'entree.
COPY alembic ./alembic
COPY alembic.ini ./
COPY scripts ./scripts
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

EXPOSE 8000
ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
