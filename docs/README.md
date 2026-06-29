# Documentation — El-Haress

Documentation de developpement et d'exploitation du depot `el-haress-app`.

> La specification de reference du projet (contexte metier, architecture,
> roadmap, systeme de design) est maintenue separement par l'equipe. Ce dossier
> couvre le travail quotidien sur le depot : mise en route, conventions et
> garde-fous du depot distant.

---

## Index

| Document                                       | Objet                                                 |
| ---------------------------------------------- | ----------------------------------------------------- |
| [setup-local.md](setup-local.md)               | Installer et lancer backend + frontend en local       |
| [conventions.md](conventions.md)               | Workflow git, format de commits, standards de code     |
| [securite-depot.md](securite-depot.md)         | Ce qui ne doit jamais partir au depot et pourquoi      |
| [sensor-system-ste2.md](sensor-system-ste2.md) | Passerelle capteurs HWg STE2 LITE : protocole, parsing, conflits |
| [database-schema.md](database-schema.md)       | Schema TimescaleDB : tables, hypertable, retention, Raspberry Pi |
| [security.md](security.md)                     | Modele de securite : auth JWT RS256, isolation, anti-abus       |

---

## Decisions figees

| Domaine          | Choix                                       |
| ---------------- | ------------------------------------------- |
| Backend          | FastAPI + Python 3.12                        |
| Base de donnees  | TimescaleDB (PostgreSQL 16)                  |
| Cache            | Redis (4 bases logiques)                     |
| Auth             | JWT RS256 + blacklist par `jti`              |
| Frontend         | React 19 + Vite + shadcn/ui + Tailwind       |
| Depot distant    | GitLab                                       |
| Deploiement      | Nginx + systemd + Cloudflare Tunnel          |
