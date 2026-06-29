# Environnement de developpement local

Mettre en place et lancer El-Haress sur un poste de developpement.

---

## 1. Prerequis

| Outil             | Version    | Verification          |
| ----------------- | ---------- | --------------------- |
| Python            | 3.12+      | `python3 --version`   |
| Node.js           | 22+        | `node --version`      |
| PostgreSQL        | 16 + TimescaleDB | `psql --version` |
| Redis             | 7+         | `redis-cli ping`      |
| git               | 2.40+      | `git --version`       |

Outils de qualite (recommandes) :

```bash
pip install pre-commit ruff
# gitleaks : voir https://github.com/gitleaks/gitleaks/releases
```

---

## 2. Configuration initiale

```bash
# 1. Variables d'environnement
cp .env.example .env
#    -> renseigner DATABASE_URL, REDIS_*, secrets Twilio/SMTP si besoin

# 2. Garde-fous git (obligatoire)
pre-commit install
pre-commit run --all-files       # premier passage sur tout le depot

# 3. Cles JWT RS256 (hors depot, dans keys/ qui est gitignore)
mkdir -p keys
openssl genpkey -algorithm RSA -out keys/private.pem -pkeyopt rsa_keygen_bits:2048
openssl rsa -in keys/private.pem -pubout -out keys/public.pem
```

> Le dossier `keys/` et les `.pem` sont ignores par git. Ne jamais les committer.

---

## 3. Base de donnees et Redis (Docker)

Le plus simple en developpement : la stack est fournie via `docker-compose.yml`
(TimescaleDB + Redis, isolee, conteneurs et volumes dedies).

```bash
docker compose up -d timescaledb      # base seule (suffit pour migrer)
docker compose up -d                  # base + redis
```

Ports hote par defaut : TimescaleDB `5432`, Redis `6380` (surchargeables via
`POSTGRES_HOST_PORT` / `REDIS_HOST_PORT` pour cohabiter avec d'autres stacks).
Aligner `DATABASE_URL` et `REDIS_PORT` du `.env` sur ces ports.

> Production sur Raspberry Pi 3 (ARM, 1 Go RAM) : voir les reglages faible-RAM et
> la compatibilite ARM dans [database-schema.md](database-schema.md) (section 8).

---

## 4. Backend (FastAPI)

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Migrations base de donnees (TimescaleDB doit tourner)
alembic upgrade head

# Lancer l'API
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

API disponible sur `http://localhost:8000`, documentation OpenAPI sur
`http://localhost:8000/api/v1/docs` (hors production uniquement).

Le collector (polling des capteurs) est un service distinct :

```bash
python -m src.collector
```

---

## 5. Frontend (React + Vite)

```bash
cd frontend
npm install
npm run dev
```

Interface disponible sur `http://localhost:5173`.

---

## 6. Verifications avant de pousser

```bash
# Backend
cd backend && ruff check . && ruff format --check . && pytest

# Frontend
cd frontend && npm run lint && npm test

# Secrets (sur tout le depot)
gitleaks detect --source . --config .gitleaks.toml
```

Tout doit passer au vert. Le detail du workflow git est dans
[conventions.md](conventions.md).
