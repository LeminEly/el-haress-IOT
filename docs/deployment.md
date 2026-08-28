# Deploiement et durcissement (Raspberry Pi)

Deploiement single-site sur Raspberry Pi 3 (Raspberry Pi OS 64 bits). Tout tourne
sur le Pi : TimescaleDB, Redis, backend (Gunicorn/Uvicorn), collector, Nginx, et
l'acces externe via Cloudflare Tunnel (aucun port ouvert sur le Pi).

```
[Pi]
  Nginx (80)  ── /         -> build React (frontend/dist)
              └─ /api/     -> 127.0.0.1:8000 (backend) + WebSocket
  el-haress-backend.service     (Gunicorn + UvicornWorker)
  el-haress-collector.service   (polling STE2 LITE)
  TimescaleDB + Redis (locaux)
  cloudflared.service           (tunnel : supervision.exemple.com -> localhost:80)
```

---

## 1. Installation automatisee

Le script `deploy/install.sh` provisionne le Pi de zero (idempotent) :

```bash
git clone <depot> /opt/el-haress/app
cd /opt/el-haress/app
sudo deploy/install.sh
```

Il installe les paquets, TimescaleDB (regle pour 1 Go RAM via `timescaledb-tune`),
Redis, construit le backend (venv + migrations) et le frontend (build), genere les
cles RS256, cree `/etc/el-haress/el-haress.env`, installe les services systemd et
la configuration Nginx, puis applique le durcissement (pare-feu, fail2ban, mises a
jour automatiques).

A la fin, creer le premier `SUPER_ADMIN` (commande affichee par le script).

---

## 2. Disposition sur le Pi

| Chemin                          | Role                                        |
| ------------------------------- | ------------------------------------------- |
| `/opt/el-haress/app`            | code (backend, frontend/dist)               |
| `/etc/el-haress/el-haress.env`  | configuration et secrets (root:el-haress 640)|
| `/etc/el-haress/keys/`          | cles RS256 (jamais au depot)                |
| `el-haress-backend.service`     | API (Gunicorn, 2 workers, 127.0.0.1:8000)   |
| `el-haress-collector.service`   | collector (process distinct)                |

Les services tournent sous l'utilisateur systeme non-root `el-haress`, avec
durcissement systemd (`ProtectSystem=strict`, `NoNewPrivileges`, etc.).

---

## 3. Acces externe — Cloudflare Tunnel

Aucun port n'est ouvert sur le Pi. Voir `deploy/cloudflared/config.example.yml` :

```bash
cloudflared tunnel login
cloudflared tunnel create el-haress
cloudflared tunnel route dns el-haress supervision.exemple.com
# config.yml -> /etc/cloudflared/config.yml
cloudflared service install
systemctl enable --now cloudflared
```

Renseigner ensuite `CORS_ORIGINS=https://supervision.exemple.com` et
`COOKIE_SECURE=true` dans l'environnement.

---

## 4. Durcissement du Pi

- **SSH** : par cle uniquement, mot de passe desactive
  (`PasswordAuthentication no`), `PermitRootLogin no`.
- **Pare-feu** : `ufw` limite a 22/80/443 (l'acces public passe par le tunnel).
- **fail2ban** : protection anti-brute-force SSH.
- **unattended-upgrades** : correctifs de securite automatiques.
- **Reseau capteurs** : le STE2 LITE est en IP statique sur un segment interne,
  jamais expose (voir [sensor-system-ste2.md](sensor-system-ste2.md)).
- **RustDesk** (si utilise) : mot de passe fort, jamais de defaut.

---

## 5. Exploitation

```bash
systemctl status el-haress-backend el-haress-collector
journalctl -u el-haress-backend -f
journalctl -u el-haress-collector -f      # cycles de collecte, capteurs muets

# Mise a jour applicative
cd /opt/el-haress/app && git pull && sudo deploy/install.sh
```

La retention 30 jours et la compression sont gerees par TimescaleDB (aucune action
manuelle). Sauvegardes : voir la phase qualite (`quality-nfr.md`).

---

## 6. Montee en charge

Le modele de donnees (isolation par `account_id`) est pret pour une plateforme
centrale : on peut deporter API + base + dashboard sur un serveur, les Pi ne
gardant que le role de collector. Seule la topologie change, pas le schema.
