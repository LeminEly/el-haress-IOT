# El-Haress

Plateforme SaaS multi-entreprises de supervision environnementale des salles
serveurs : mesure temps reel (temperature, puis fumee, humidite, mouvement),
tableau de bord par entreprise, alertes multi-canal (WhatsApp / SMS / Email) et
retention automatique des donnees a 30 jours.

Application critique d'infrastructure, livree en production reelle. Fiabilite,
isolation stricte des donnees entre entreprises et securite sont non negociables.

---

## Stack

| Domaine          | Choix                                              |
| ---------------- | -------------------------------------------------- |
| Backend          | FastAPI + Python 3.12 (async)                      |
| Base de donnees  | TimescaleDB (extension PostgreSQL 16)              |
| ORM / migrations | SQLAlchemy 2.0 (async) + Alembic                   |
| Cache / files    | Redis (cache, rate limit, dedup, blacklist JWT)    |
| Frontend         | React 19 + Vite + TypeScript + shadcn/ui + Tailwind|
| Temps reel       | WebSocket (FastAPI natif)                          |
| Auth             | JWT RS256 (cle privee backend, stateless)          |
| Notifications    | Twilio (WhatsApp + SMS) + SMTP (Email)             |
| Deploiement      | Nginx + systemd + Cloudflare Tunnel                |

---

## Structure du depot

```
backend/    API FastAPI + collector + moteur d'alertes + tenancy (Python)
frontend/   tableau de bord React 19 + TypeScript
deploy/     configuration Nginx, systemd, Cloudflare Tunnel
docs/        documentation de developpement et d'exploitation
scripts/    utilitaires
```

---

## Demarrage rapide

Les instructions detaillees (prerequis, base de donnees, lancement) sont dans
[docs/setup-local.md](docs/setup-local.md).

```bash
cp .env.example .env          # renseigner les variables locales
pip install pre-commit
pre-commit install            # active les garde-fous git locaux
```

---

## Documentation

Voir le dossier [docs/](docs/) :

- [docs/README.md](docs/README.md) — index de la documentation
- [docs/setup-local.md](docs/setup-local.md) — environnement de developpement
- [docs/conventions.md](docs/conventions.md) — git, commits, standards de code
- [docs/securite-depot.md](docs/securite-depot.md) — ce qui ne doit jamais partir au depot

---

## Regles absolues

- **Isolation multi-entreprises** : un compte = une entreprise. L'`account_id`
  vient toujours du jeton JWT, jamais d'un parametre client. Aucune fuite
  cross-tenant, verifiee par tests.
- **Genericite** : aucune valeur metier en dur (seuils, capteurs, intervalles).
- **Retention 30 jours** : suppression automatique par TimescaleDB.
- **Securite d'abord** : en cas de doute, choisir la securite.
- **Discipline git** : aucun push sans confirmation explicite ; jamais de push
  direct sur `main` ou `develop`.
