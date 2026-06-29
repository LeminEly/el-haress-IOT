#!/usr/bin/env bash
#
# Provisionnement d'un Raspberry Pi (Raspberry Pi OS 64 bits) pour El-Haress :
# TimescaleDB, Redis, backend (Gunicorn/Uvicorn), collector, Nginx, durcissement.
#
# Idempotent : relançable sans casser une installation existante.
# Usage :  sudo deploy/install.sh
#
set -euo pipefail

APP_USER="el-haress"
APP_ROOT="/opt/el-haress/app"
ETC_DIR="/etc/el-haress"
KEYS_DIR="${ETC_DIR}/keys"
ENV_FILE="${ETC_DIR}/el-haress.env"
PG_DB="el_haress"
PG_USER="el_haress"

SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

log() { echo -e "\n[\033[0;36mel-haress\033[0m] $*"; }

require_root() {
  if [[ "${EUID}" -ne 0 ]]; then
    echo "Ce script doit etre execute en root (sudo)." >&2
    exit 1
  fi
}

install_packages() {
  log "Installation des paquets systeme"
  export DEBIAN_FRONTEND=noninteractive
  apt-get update -y
  apt-get install -y --no-install-recommends \
    ca-certificates curl gnupg lsb-release \
    nginx redis-server \
    python3 python3-venv python3-dev build-essential libpq-dev \
    ufw fail2ban unattended-upgrades openssl rsync
}

install_node() {
  if ! command -v node >/dev/null 2>&1; then
    log "Installation de Node.js (build du frontend)"
    curl -fsSL https://deb.nodesource.com/setup_22.x | bash -
    apt-get install -y nodejs
  fi
}

install_timescaledb() {
  if ! dpkg -l | grep -q timescaledb-2-postgresql; then
    log "Installation de TimescaleDB (PostgreSQL 16)"
    echo "deb https://packagecloud.io/timescale/timescaledb/debian/ $(lsb_release -cs) main" \
      >/etc/apt/sources.list.d/timescaledb.list
    curl -fsSL https://packagecloud.io/timescale/timescaledb/gpgkey \
      | gpg --dearmor -o /etc/apt/trusted.gpg.d/timescaledb.gpg
    apt-get update -y
    apt-get install -y timescaledb-2-postgresql-16 postgresql-client-16
    # Reglage memoire (adapte au Pi 3, 1 Go RAM).
    timescaledb-tune --quiet --yes || true
    systemctl restart postgresql
  fi
}

create_user() {
  if ! id "${APP_USER}" >/dev/null 2>&1; then
    log "Creation de l'utilisateur systeme ${APP_USER}"
    useradd --system --create-home --shell /usr/sbin/nologin "${APP_USER}"
  fi
}

deploy_code() {
  log "Deploiement du code dans ${APP_ROOT}"
  mkdir -p "${APP_ROOT}"
  rsync -a --delete \
    --exclude '.git' --exclude '.venv' --exclude 'node_modules' \
    --exclude 'frontend/dist' --exclude 'keys' \
    "${SRC_DIR}/" "${APP_ROOT}/"
}

setup_secrets() {
  mkdir -p "${ETC_DIR}" "${KEYS_DIR}"
  if [[ ! -f "${KEYS_DIR}/private.pem" ]]; then
    log "Generation de la paire de cles RS256"
    openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:2048 -out "${KEYS_DIR}/private.pem"
    openssl rsa -in "${KEYS_DIR}/private.pem" -pubout -out "${KEYS_DIR}/public.pem"
  fi
  if [[ ! -f "${ENV_FILE}" ]]; then
    log "Creation de ${ENV_FILE} (a completer avec les secrets reels)"
    local db_password
    db_password="$(openssl rand -hex 16)"
    sed "s#postgresql+asyncpg://el_haress:CHANGER@#postgresql+asyncpg://${PG_USER}:${db_password}@#" \
      "${SRC_DIR}/deploy/el-haress.env.example" >"${ENV_FILE}"
    echo "DB_BOOTSTRAP_PASSWORD=${db_password}" >"${ETC_DIR}/.db-bootstrap"
    chmod 600 "${ETC_DIR}/.db-bootstrap"
  fi
  chown -R root:"${APP_USER}" "${ETC_DIR}"
  chmod 750 "${ETC_DIR}" "${KEYS_DIR}"
  chmod 640 "${ENV_FILE}" "${KEYS_DIR}/private.pem" "${KEYS_DIR}/public.pem"
}

setup_database() {
  log "Configuration de la base ${PG_DB}"
  local db_password
  db_password="$(grep -oP 'DB_BOOTSTRAP_PASSWORD=\K.*' "${ETC_DIR}/.db-bootstrap" 2>/dev/null || true)"
  sudo -u postgres psql -tc "SELECT 1 FROM pg_roles WHERE rolname='${PG_USER}'" | grep -q 1 || {
    sudo -u postgres psql -c "CREATE ROLE ${PG_USER} LOGIN PASSWORD '${db_password}';"
  }
  sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname='${PG_DB}'" | grep -q 1 || {
    sudo -u postgres psql -c "CREATE DATABASE ${PG_DB} OWNER ${PG_USER};"
  }
  sudo -u postgres psql -d "${PG_DB}" -c "CREATE EXTENSION IF NOT EXISTS timescaledb;"
}

build_backend() {
  log "Construction du backend (venv + migrations)"
  python3 -m venv "${APP_ROOT}/backend/.venv"
  "${APP_ROOT}/backend/.venv/bin/pip" install --upgrade pip
  "${APP_ROOT}/backend/.venv/bin/pip" install -e "${APP_ROOT}/backend"
  ( cd "${APP_ROOT}/backend" && set -a && . "${ENV_FILE}" && set +a \
    && "${APP_ROOT}/backend/.venv/bin/alembic" upgrade head )
}

build_frontend() {
  log "Construction du frontend (build de production)"
  ( cd "${APP_ROOT}/frontend" && npm ci && npm run build )
}

setup_services() {
  log "Installation des services systemd"
  install -m 644 "${SRC_DIR}/deploy/systemd/el-haress-backend.service" /etc/systemd/system/
  install -m 644 "${SRC_DIR}/deploy/systemd/el-haress-collector.service" /etc/systemd/system/
  chown -R "${APP_USER}:${APP_USER}" "${APP_ROOT}"
  systemctl daemon-reload
  systemctl enable --now el-haress-backend.service el-haress-collector.service
}

setup_nginx() {
  log "Configuration de Nginx"
  install -m 644 "${SRC_DIR}/deploy/nginx/el-haress-security-headers.conf" \
    /etc/nginx/snippets/el-haress-security-headers.conf
  install -m 644 "${SRC_DIR}/deploy/nginx/el-haress.conf" \
    /etc/nginx/sites-available/el-haress.conf
  ln -sf /etc/nginx/sites-available/el-haress.conf /etc/nginx/sites-enabled/el-haress.conf
  rm -f /etc/nginx/sites-enabled/default
  nginx -t
  systemctl reload nginx
}

harden() {
  log "Durcissement (pare-feu, fail2ban, mises a jour automatiques)"
  ufw allow 22/tcp
  ufw allow 80/tcp
  ufw allow 443/tcp
  ufw --force enable
  systemctl enable --now fail2ban
  dpkg-reconfigure -f noninteractive unattended-upgrades || true
}

main() {
  require_root
  install_packages
  install_node
  install_timescaledb
  create_user
  deploy_code
  setup_secrets
  setup_database
  build_backend
  build_frontend
  setup_services
  setup_nginx
  harden
  log "Installation terminee. Creer le premier compte :"
  echo "  sudo -u ${APP_USER} bash -c 'set -a; . ${ENV_FILE}; ${APP_ROOT}/backend/.venv/bin/python ${APP_ROOT}/backend/scripts/create_superadmin.py --phone +222XXXXXXXX --company \"Operateur\"'"
}

main "$@"
