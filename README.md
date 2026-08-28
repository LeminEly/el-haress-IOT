# El-Haress

Plateforme SaaS **multi-entreprises** de supervision environnementale des salles
serveurs. Des capteurs (temperature, puis fumee, humidite, mouvement) relies a un
Raspberry Pi via une passerelle **STE2 Lite** mesurent en continu les conditions
d'une salle. Les mesures sont stockees, **isolees par entreprise**, affichees en
temps reel sur un tableau de bord, et declenchent des **alertes multi-canal**
(WhatsApp / SMS / Email) au-dela d'un seuil configurable. Les donnees de mesure
sont conservees **30 jours**, puis supprimees automatiquement.

Application critique d'infrastructure, livree en production reelle. Fiabilite,
isolation stricte des donnees entre entreprises et securite sont non negociables.

---

## Sommaire

1. [Apercu fonctionnel](#apercu-fonctionnel)
2. [Stack technique](#stack-technique)
3. [Architecture](#architecture)
4. [Structure du depot](#structure-du-depot)
5. [Prerequis](#prerequis)
6. [Lancer le projet en local](#lancer-le-projet-en-local)
7. [Premiere connexion](#premiere-connexion)
8. [Variables d'environnement](#variables-denvironnement)
9. [Tests, lint et qualite](#tests-lint-et-qualite)
10. [Integration continue](#integration-continue)
11. [Deploiement](#deploiement)
12. [Regles absolues du projet](#regles-absolues-du-projet)
13. [Documentation](#documentation)

---

## Apercu fonctionnel

- **Multi-entreprises** : une seule plateforme dessert plusieurs entreprises,
  chacune totalement isolee des autres. Un compte = une entreprise.
- **Deux roles** : `SUPER_ADMIN` (exploitant : cree et gere les comptes
  entreprises) et `COMPANY` (entreprise cliente : acces a ses seules donnees).
- **Mesure temps reel** : un collector interroge la passerelle STE2 a intervalle
  configurable et enregistre les mesures.
- **Tableau de bord** : tous les capteurs affiches ensemble (chacun avec son seuil
  et sa couleur de courbe), plus une vue detaillee par capteur.
- **Alertes** : au franchissement d'un seuil, notification WhatsApp / SMS / Email
  avec deduplication et cooldown.
- **Retention 30 jours** : suppression automatique native (TimescaleDB), jamais
  par script applicatif.

---

## Stack technique

| Domaine            | Choix                                                   |
| ------------------ | ------------------------------------------------------- |
| Backend            | FastAPI + Python 3.12 (async)                           |
| Serveur ASGI       | Uvicorn (dev) / Gunicorn + Uvicorn workers (prod)       |
| Base de donnees    | TimescaleDB (extension PostgreSQL 16)                   |
| ORM / migrations   | SQLAlchemy 2.0 (async) + Alembic                        |
| Cache / files      | Redis (cache, rate limit, dedup alertes, blacklist JWT) |
| Collector          | Service Python asyncio dedie                            |
| Frontend           | React 19 + Vite + TypeScript + shadcn/ui + Tailwind CSS |
| Graphiques         | Recharts                                                |
| Temps reel         | WebSocket (FastAPI natif)                               |
| Auth               | JWT RS256 (cle privee backend, stateless)               |
| i18n               | i18next (FR / AR / EN)                                   |
| Notifications      | Twilio (WhatsApp + SMS) + SMTP (Email)                  |
| Deploiement        | Nginx + systemd + Cloudflare Tunnel                     |

**Redis — bases logiques separees :** DB 0 cache · DB 1 rate limit · DB 2
deduplication des alertes · DB 3 blacklist JWT.

---

## Architecture

```
Capteurs --> STE2 Lite --> [ Collector (asyncio) ] --> TimescaleDB
                                   |                        ^
                                   v                        |
                          [ Moteur d'alertes ] ---> Notifications (WhatsApp/SMS/Email)
                                                            |
   Navigateur <--- Nginx <--- [ API FastAPI + WebSocket ] --+
                                   |
                                 Redis (cache / rate limit / dedup / blacklist)
```

L'`account_id` provient **toujours** du jeton JWT et filtre chaque requete de la
couche service. Aucune entreprise ne peut acceder aux donnees d'une autre.

---

## Structure du depot

```
backend/      API FastAPI + collector + moteur d'alertes + tenancy (Python)
  src/        code applicatif (auth, sensors, collector, alerting, api, ...)
  alembic/    migrations de base de donnees versionnees
  scripts/    utilitaires (creation du super-admin)
  tests/      tests unitaires et anti-fuite cross-tenant
frontend/     tableau de bord React 19 + TypeScript
deploy/       Nginx, systemd, Cloudflare Tunnel, install.sh
docs/         documentation de developpement et d'exploitation
docker-compose.yml   stack locale (TimescaleDB + Redis)
```

---

## Prerequis

- **Docker** + **Docker Compose** (pour TimescaleDB et Redis en local)
- **Python 3.12+**
- **Node.js 22+** et **npm**
- **OpenSSL** (generation des cles JWT RS256)

> Tout se lance en local. Aucune dependance cloud n'est requise pour developper
> (Twilio et SMTP sont optionnels ; sans eux, les alertes sont seulement logguees).

---

## Lancer le projet en local

Quatre composants tournent ensemble : **base + Redis** (Docker), **API**,
**collector**, **frontend**. Ouvre un terminal par service.

### 1. Cloner et configurer l'environnement

```bash
git clone https://gitlab.awlyg.tech/iot-el-haress/el-haress-app.git
cd el-haress-app
cp .env.example .env
```

Edite `.env` si besoin. Pour coller a la stack Docker fournie, mets Redis sur le
port expose par Compose :

```env
REDIS_PORT=6380
```

### 2. Demarrer la base de donnees et Redis

```bash
docker compose up -d
```

TimescaleDB ecoute sur `localhost:5432`, Redis sur `localhost:6380`.

### 3. Backend — API

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# Cles JWT RS256 (hors depot, dans keys/ qui est gitignore)
mkdir -p keys
openssl genpkey -algorithm RSA -out keys/private.pem -pkeyopt rsa_keygen_bits:2048
openssl rsa -in keys/private.pem -pubout -out keys/public.pem

# Migrations (cree le schema, l'hypertable, la retention 30 jours)
alembic upgrade head

# Lancer l'API
uvicorn src.main:app --reload --port 8000
```

- API : http://localhost:8000
- Documentation OpenAPI : http://localhost:8000/docs
- Sante du service : http://localhost:8000/api/v1/health

### 4. Collector (polling des capteurs)

Dans un autre terminal, avec le venv active (`source backend/.venv/bin/activate`) :

```bash
cd backend
python -m src.collector
```

> Le collector lit l'URL de la passerelle dans `STE2_BASE_URL`. Si la passerelle
> est injoignable, il reste resilient et reessaie ; aucune valeur de capteur ou
> de seuil n'est codee en dur.

### 5. Frontend — tableau de bord

```bash
cd frontend
npm install
npm run dev
```

Interface : http://localhost:5173

---

## Premiere connexion

Aucune auto-inscription : le premier compte est un **SUPER_ADMIN** cree en ligne
de commande. Depuis `backend/` (venv active, base accessible) :

```bash
python scripts/create_superadmin.py --phone +2224XXXXXX --company "Operateur"
```

Le mot de passe est demande de maniere interactive (jamais en argument, jamais
logge). Connecte-toi ensuite sur le frontend avec ce numero et ce mot de passe,
puis cree les comptes entreprises depuis l'interface d'administration.

> L'identifiant de connexion est le **numero de telephone**, normalise au format
> international (region par defaut configurable via `DEFAULT_PHONE_REGION`).

---

## Variables d'environnement

Toutes les variables sont documentees dans [.env.example](.env.example). Les plus
importantes :

| Variable                        | Role                                             |
| ------------------------------- | ------------------------------------------------ |
| `ENVIRONMENT`                   | `development` ou `production`                     |
| `DATABASE_URL`                  | connexion TimescaleDB (asyncpg)                   |
| `REDIS_HOST` / `REDIS_PORT`     | connexion Redis (`6380` avec la stack Docker)     |
| `READINGS_RETENTION_DAYS`       | retention des mesures (30, gere par TimescaleDB)  |
| `JWT_PRIVATE_KEY_PATH` / `..._PUBLIC_...` | cles RS256 (hors depot)                  |
| `CORS_ORIGINS`                  | whitelist explicite, jamais `*` en production     |
| `STE2_BASE_URL`                 | URL de la passerelle capteurs                     |
| `COLLECTOR_POLL_INTERVAL_SECONDS` | intervalle de polling                          |
| `TWILIO_*` / `SMTP_*`           | notifications (optionnel en local)                |
| `COOKIE_SECURE`                 | `true` obligatoire en production (HTTPS)           |

> Ne jamais committer de `.env` reel ni le dossier `keys/`. Les secrets vivent
> uniquement dans l'environnement.

---

## Tests, lint et qualite

**Backend** (depuis `backend/`, base de test accessible, cles JWT presentes) :

```bash
pytest --cov=src --cov-report=term-missing --cov-fail-under=80
ruff check src/
ruff format --check src/
```

**Frontend** (depuis `frontend/`) :

```bash
npm run lint
npm run build      # typecheck tsc + build de production
```

La couverture des services doit rester **>= 80 %**, avec des tests **anti-fuite
cross-tenant** pour chaque fonctionnalite.

---

## Integration continue

Le pipeline GitLab ([.gitlab-ci.yml](.gitlab-ci.yml)) comporte trois etapes :

| Etape      | Jobs                                                          |
| ---------- | ------------------------------------------------------------- |
| `security` | `gitleaks` (secrets, bloquant), `sast-semgrep`, `trivy`       |
| `lint`     | `backend-lint` (ruff), `frontend-lint` (eslint + prettier)    |
| `test`     | `backend-test` (pytest sur TimescaleDB), `frontend-build`     |

Un commit qui introduit un secret, casse le lint, les tests ou le build ne passe
pas la chaine.

**Modele de branches :** `main` (protegee) ne contient que ce README ; tout le
travail vit sur `development` ; chaque changement passe par une **merge request
vers `development`** ; la fusion `development -> main` est l'etape finale.

---

## Deploiement

Le provisioning d'un Raspberry Pi de zero est decrit dans
[docs/deployment.md](docs/deployment.md), avec :

- services **systemd** (`el-haress-backend`, `el-haress-collector`),
- **Nginx** (statique React + proxy API + WebSocket),
- **Cloudflare Tunnel** (acces externe, aucun port ouvert sur le Pi),
- durcissement (SSH par cle, `ufw`, `fail2ban`, `unattended-upgrades`, user
  systeme non-root),
- script `deploy/install.sh`.

---

## Regles absolues du projet

- **Isolation multi-entreprises** : un compte = une entreprise. L'`account_id`
  vient toujours du jeton JWT, jamais d'un parametre client. Aucune fuite
  cross-tenant, verifiee par tests.
- **Genericite** : aucune valeur metier en dur (seuils, capteurs, intervalles,
  destinataires, retention) — tout est en base ou en configuration.
- **Retention 30 jours** : suppression automatique par TimescaleDB.
- **Securite d'abord** : en cas de doute entre simplicite et securite, choisir la
  securite.
- **Discipline git** : aucun push sans confirmation explicite ; jamais de push
  direct sur `main` ou `develop`.

---

## Documentation

Voir le dossier [docs/](docs/) :

- [docs/README.md](docs/README.md) — index de la documentation
- [docs/setup-local.md](docs/setup-local.md) — environnement de developpement
- [docs/api-reference.md](docs/api-reference.md) — endpoints REST + WebSocket
- [docs/database-schema.md](docs/database-schema.md) — schema TimescaleDB
- [docs/security.md](docs/security.md) — securite et isolation cross-tenant
- [docs/alerting-rules.md](docs/alerting-rules.md) — configuration des seuils
- [docs/deployment.md](docs/deployment.md) — provisioning et durcissement du Pi
- [docs/conventions.md](docs/conventions.md) — git, commits, standards de code
