# Reference API

API REST + WebSocket d'El-Haress. Prefixe : `/api/v1`. OpenAPI interactif sur
`/api/v1/docs` (hors production).

## Contrat

- Succes : `{ "data": <T>, "message": "<optionnel>" }`
- Erreur (RFC 7807) : `{ "type", "title", "status", "request_id" }`
  (`application/problem+json`)
- Authentification : `Authorization: Bearer <access_token>` sur toutes les routes
  sauf `POST /auth/login` et `POST /auth/refresh`.
- Toutes les donnees sont filtrees par l'`account_id` du jeton (isolation).

## Authentification

| Methode | Chemin              | Role     | Description                          |
| ------- | ------------------- | -------- | ------------------------------------ |
| POST    | `/auth/login`       | public   | telephone + mot de passe -> jetons   |
| POST    | `/auth/refresh`     | cookie   | rotation du refresh -> nouvel access |
| POST    | `/auth/logout`      | auth     | revocation des jetons courants       |
| GET     | `/auth/me`          | auth     | profil du compte authentifie         |

## Comptes (SUPER_ADMIN)

| Methode | Chemin               | Description                         |
| ------- | -------------------- | ----------------------------------- |
| POST    | `/accounts`          | creer un compte entreprise          |
| GET     | `/accounts`          | lister les comptes                  |
| PATCH   | `/accounts/{id}`     | activer / suspendre                 |

## Passerelles et capteurs (entreprise)

| Methode | Chemin               | Description                          |
| ------- | -------------------- | ------------------------------------ |
| GET     | `/gateways`          | passerelles de l'entreprise          |
| POST    | `/gateways`          | declarer une passerelle (STE2)       |
| GET     | `/sensors`           | capteurs de l'entreprise             |
| PATCH   | `/sensors/{id}`      | editer libelle / type / activation   |

## Mesures et tableau de bord

| Methode | Chemin                 | Parametres                                  |
| ------- | ---------------------- | ------------------------------------------- |
| GET     | `/readings`            | `sensor_id`, `start`, `end`, `bucket`, `limit` |
| GET     | `/readings/latest`     | derniere valeur par capteur                  |
| GET     | `/dashboard/summary`   | agregats de la vue d'ensemble                |

`bucket` : `raw` (defaut), `1min`, `1hour` (agregats continus). `limit` <= 5000.

## Regles d'alerte (entreprise)

| Methode | Chemin                 | Description                |
| ------- | ---------------------- | -------------------------- |
| GET     | `/alert-rules`         | lister                     |
| POST    | `/alert-rules`         | creer (seuil configurable) |
| PATCH   | `/alert-rules/{id}`    | modifier                   |
| DELETE  | `/alert-rules/{id}`    | supprimer                  |

## Alertes declenchees

| Methode | Chemin                | Description                          |
| ------- | --------------------- | ------------------------------------ |
| GET     | `/alerts`             | historique (filtre `status`)         |
| POST    | `/alerts/{id}/ack`    | acquitter une alerte                 |

## Temps reel

| Type      | Chemin                     | Description                                  |
| --------- | -------------------------- | -------------------------------------------- |
| WebSocket | `/ws/live?token=<access>`  | flux des nouvelles mesures de l'entreprise   |

Le collector publie chaque mesure sur le canal Redis `live:{account_id}` ; le
WebSocket relaie uniquement le canal de l'entreprise authentifiee (isolation
stricte). Chaque message : `{ "sensor_id", "value", "recorded_at" }`.
