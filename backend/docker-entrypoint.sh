#!/bin/sh
# Point d'entree commun API / collector.
# - genere des cles JWT de developpement si absentes (en production : monter de
#   vraies cles, ne jamais dependre de cette generation) ;
# - applique les migrations uniquement pour le service qui porte RUN_MIGRATIONS=1
#   (evite que l'API et le collector migrent en meme temps).
set -e

if [ ! -f keys/private.pem ]; then
  echo "generation de cles JWT de developpement (keys/ vide)"
  mkdir -p keys
  python - <<'PY'
from cryptography.hazmat.primitives import serialization as s
from cryptography.hazmat.primitives.asymmetric import rsa

key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
with open("keys/private.pem", "wb") as f:
    f.write(key.private_bytes(s.Encoding.PEM, s.PrivateFormat.PKCS8, s.NoEncryption()))
with open("keys/public.pem", "wb") as f:
    f.write(key.public_key().public_bytes(s.Encoding.PEM, s.PublicFormat.SubjectPublicKeyInfo))
PY
fi

if [ "$RUN_MIGRATIONS" = "1" ]; then
  echo "application des migrations..."
  i=1
  while [ "$i" -le 30 ]; do
    if alembic upgrade head; then
      break
    fi
    echo "base indisponible, nouvelle tentative ($i/30)..."
    i=$((i + 1))
    sleep 2
  done
fi

exec "$@"
