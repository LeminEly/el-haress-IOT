# Modele de securite — authentification et isolation

Securite by design d'El-Haress. La priorite absolue est l'isolation des donnees
entre entreprises ; viennent ensuite l'authentification forte et les protections
contre les abus.

---

## 1. Authentification

| Aspect            | Choix                                                        |
| ----------------- | ------------------------------------------------------------ |
| Identifiant       | Numero de telephone, normalise en E.164 (`phonenumbers`)     |
| Mot de passe      | bcrypt (cout 12), pre-hache SHA-256 (leve la limite 72 octets) |
| Jetons            | JWT **RS256** (cle privee cote backend uniquement)           |
| Access token      | Bearer, courte duree (15 min), porte `sub`, `role`, `jti`     |
| Refresh token     | Cookie **httpOnly**, **SameSite=Strict**, `Secure` en prod    |
| Rotation refresh  | A chaque `/auth/refresh` : l'ancien `jti` est revoque         |
| Logout            | Revocation (blacklist Redis) de l'access et du refresh        |

Routes publiques : `POST /auth/login`, `POST /auth/refresh`. Toutes les autres
exigent un access token valide.

### Flux

```
login (telephone + mot de passe)
  -> access token (Bearer)  +  refresh token (cookie httpOnly)
       -> chaque requete protegee : Authorization: Bearer <access>
       -> /auth/refresh : rotation, nouveau couple de jetons
       -> /auth/logout  : revocation des jetons courants
```

---

## 2. Isolation multi-entreprises (priorite maximale)

- `account_id` **NOT NULL** sur toutes les tables metier (schema).
- Le perimetre de donnees vient **uniquement du jeton** (`Principal.account_id`),
  jamais d'un parametre de requete. La dependance `tenancy.get_tenant_context`
  est la seule source de l'`account_id` pour la couche service.
- Un `account_id` fourni en query/body est ignore (test dedie).
- RBAC : `require_role(SUPER_ADMIN)` protege la gestion des comptes ; un compte
  `COMPANY` ne peut ni lister ni creer de comptes (403).
- Index composites prefixes par `account_id` (isolation + performance).

> Les tests anti-fuite cross-tenant sur les donnees (capteurs, mesures) seront
> completes avec les endpoints de donnees (phase 4). Le point d'application de
> l'isolation — la dependance de tenance — est en place et teste des maintenant.

---

## 3. Protections contre les abus

| Menace            | Protection                                                   |
| ----------------- | ------------------------------------------------------------ |
| Force brute       | Lockout apres 5 echecs -> verrou 15 min (persiste en base)   |
| Flood login       | Rate limit Redis a fenetre glissante (10 req/min par IP)     |
| Enumeration       | Messages d'erreur generiques ("Identifiants invalides")      |
| Mass assignment   | Pydantic strict (`extra="forbid"`) sur toutes les entrees    |
| Rejeu de jeton    | `jti` + blacklist Redis (logout, rotation)                   |
| Vol de cookie     | refresh token httpOnly + SameSite=Strict + Secure (prod)     |

---

## 4. En-tetes de securite

Appliques a chaque reponse : `X-Content-Type-Options: nosniff`,
`X-Frame-Options: DENY`, `Referrer-Policy: no-referrer`,
`Content-Security-Policy: default-src 'none'; frame-ancestors 'none'`,
`Cross-Origin-Opener-Policy: same-origin`. **HSTS** ajoute en production (HTTPS).

---

## 5. Gestion des secrets et des cles

- Paire RS256 generee hors depot (`keys/`, gitignore). La cle privee n'est lue
  que par le backend, via un chemin en configuration.
- Tous les secrets (cles, mots de passe SMTP/Twilio) en variables d'environnement.
- Aucune auto-inscription : le premier `SUPER_ADMIN` est cree par le script
  `backend/scripts/create_superadmin.py` (mot de passe saisi interactivement).

---

## 6. Production

- `COOKIE_SECURE=true` (cookies uniquement via HTTPS).
- `CORS_ORIGINS` en whitelist explicite, jamais `*`.
- Pas de stack trace exposee (erreurs generiques, RFC 7807).
- Acces externe via Cloudflare Tunnel ; la base et Redis ne sont jamais exposes.
