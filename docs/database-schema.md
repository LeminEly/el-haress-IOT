# Schema de base de donnees — TimescaleDB

Schema complet d'El-Haress : PostgreSQL 16 + extension TimescaleDB. Isolation
multi-entreprises par `account_id`, mesures en hypertable avec retention 30 jours
automatique. Les migrations sont versionnees (Alembic) ; ce document decrit l'etat
cible.

> Cible de deploiement : Raspberry Pi 3 (ARM, 1 Go RAM). Voir la section 8 pour
> les contraintes et reglages specifiques.

---

## 1. Principes transverses

- **Identifiants** : `uuid` sur toutes les tables (jamais d'entier sequentiel
  expose). Exception : `readings` (hypertable) est identifiee par
  (`sensor_id`, `recorded_at`).
- **Isolation** : `account_id` **NOT NULL** sur chaque table metier ; il vient du
  jeton JWT en couche service, jamais d'un parametre client.
- **Horodatage** : `created_at` / `updated_at` (TIMESTAMPTZ, UTC) sur les tables
  metier. Les mesures sont datees cote serveur (l'horloge de la passerelle n'est
  pas fiable).
- **Index composites** prefixes par `account_id` (isolation + performance).
- **Enums** stockes en VARCHAR avec contrainte CHECK (pas de type enum natif PG :
  migrations plus simples).
- **Nommage** : `snake_case` ; contraintes/index nommes par convention stable.

---

## 2. Tables

### accounts — comptes entreprises (unite de tenance)

Un compte = une entreprise. C'est la racine de tenance : pas d'`account_id` propre.

| Colonne        | Type         | Notes                                          |
| -------------- | ------------ | ---------------------------------------------- |
| id             | uuid PK      |                                                |
| phone_number   | varchar(32)  | **unique**, format international (`+222...`)    |
| password_hash  | varchar(255) | bcrypt, jamais en clair                         |
| company_name   | varchar(255) |                                                |
| role           | varchar      | `SUPER_ADMIN` \| `COMPANY` (CHECK)              |
| status         | varchar      | `ACTIVE` \| `SUSPENDED` (CHECK)                 |
| created_at / updated_at | timestamptz |                                       |

### sensors — capteurs declares

| Colonne      | Type         | Notes                                              |
| ------------ | ------------ | -------------------------------------------------- |
| id           | uuid PK      |                                                    |
| account_id   | uuid FK NN   | -> accounts(id) ON DELETE CASCADE                  |
| hardware_id  | varchar(64)  | identite stable (SenId 1-Wire du STE2)             |
| gateway_ref  | varchar(64)  | reference passerelle (informative)                 |
| label        | varchar(255) | libelle editable                                   |
| kind         | varchar(64)  | generique : `temperature`, `flood`, ... (jamais en dur) |
| unit         | varchar(16)  | `C`, `%`, ...                                       |
| is_active    | boolean      |                                                    |

Contraintes : `UNIQUE (account_id, hardware_id)` ; index `(account_id)`.

### readings — mesures (HYPERTABLE TimescaleDB)

Partitionnee par `recorded_at`. Pas d'identifiant surrogate (bonne pratique
time-series). Cle primaire `(sensor_id, recorded_at)` — inclut la colonne de
partitionnement, requis par TimescaleDB.

| Colonne      | Type        | Notes                                  |
| ------------ | ----------- | -------------------------------------- |
| account_id   | uuid FK NN  | -> accounts(id) ON DELETE CASCADE      |
| sensor_id    | uuid FK NN  | -> sensors(id) ON DELETE CASCADE (PK)  |
| recorded_at  | timestamptz | cle de partitionnement (PK), UTC        |
| value        | double      | mesure                                  |

Index composites : `(account_id, recorded_at)` et
`(account_id, sensor_id, recorded_at)`.

### alert_rules — regles de seuils configurables

Aucun seuil en dur : tout vit ici, par entreprise.

| Colonne          | Type         | Notes                                       |
| ---------------- | ------------ | ------------------------------------------- |
| id               | uuid PK      |                                             |
| account_id       | uuid FK NN   | -> accounts(id)                             |
| sensor_id        | uuid FK NULL | -> sensors(id) (regle ciblee ou globale)    |
| name             | varchar(255) |                                             |
| condition        | varchar      | `GT` \| `GTE` \| `LT` \| `LTE` (CHECK)        |
| threshold        | double       |                                             |
| duration_seconds | integer      | gate anti-pic                               |
| cooldown_minutes | integer      | anti-spam                                   |
| severity         | varchar      | `INFO`\|`WARNING`\|`CRITICAL`\|`EMERGENCY`   |
| channels         | jsonb        | ex. `["whatsapp","sms","email"]`            |
| is_active        | boolean      |                                             |

Index `(account_id, sensor_id)`.

### alerts — historique des declenchements

| Colonne         | Type         | Notes                                       |
| --------------- | ------------ | ------------------------------------------- |
| id              | uuid PK      |                                             |
| account_id      | uuid FK NN   | -> accounts(id)                             |
| alert_rule_id   | uuid FK NULL | -> alert_rules(id) ON DELETE SET NULL        |
| sensor_id       | uuid FK NULL | -> sensors(id) ON DELETE SET NULL            |
| severity        | varchar      | idem alert_rules                            |
| value           | double       | valeur ayant declenche                       |
| status          | varchar      | `ACTIVE`\|`ACKNOWLEDGED`\|`RESOLVED`         |
| triggered_at    | timestamptz  |                                             |
| acknowledged_at | timestamptz  | nullable                                     |

Index `(account_id, triggered_at)`.

### audit_log — journal append-only

| Colonne          | Type         | Notes                                      |
| ---------------- | ------------ | ------------------------------------------ |
| id               | uuid PK      |                                            |
| actor_account_id | uuid FK NULL | qui a agi (-> accounts, SET NULL)          |
| account_id       | uuid FK NULL | entreprise concernee (nullable : actions plateforme) |
| action           | varchar(100) |                                            |
| entity_type      | varchar(100) | nullable                                   |
| entity_id        | uuid         | nullable                                   |
| data             | jsonb        | nullable                                   |
| created_at       | timestamptz  |                                            |

**Append-only** : un trigger `BEFORE UPDATE OR DELETE` (`el_haress_audit_log_append_only`)
leve une exception. Aucune mutation possible.

---

## 3. Hypertable, retention, compression

```sql
SELECT create_hypertable('readings', by_range('recorded_at'));
ALTER TABLE readings SET (
  timescaledb.compress,
  timescaledb.compress_segmentby = 'account_id, sensor_id',
  timescaledb.compress_orderby   = 'recorded_at DESC'
);
SELECT add_compression_policy('readings', INTERVAL '6 hours');
SELECT add_retention_policy('readings', INTERVAL '30 days');
```

- **Retention 30 jours** : suppression automatique en tache de fond TimescaleDB.
  Aucun cron applicatif. C'est une regle absolue du projet.
- **Compression** apres 6 h : reduit fortement le volume disque (essentiel sur
  carte SD du Pi).

---

## 4. Agregats continus (dashboard)

Materialises et rafraichis automatiquement, groupes par `account_id` :

| Vue             | Bucket   | Refresh        | Usage                       |
| --------------- | -------- | -------------- | --------------------------- |
| `readings_1min` | 1 minute | toutes les 1 min | vues temps reel / courtes  |
| `readings_1hour`| 1 heure  | toutes les 1 h | historique long (30 j)      |

Chacune expose `avg_value`, `min_value`, `max_value` par capteur. Elles
deportent le cout d'agregation hors du chemin de requete : crucial sur le CPU
faible du Pi.

---

## 5. Isolation multi-entreprises

- `account_id` NOT NULL sur `sensors`, `readings`, `alert_rules`, `alerts`.
- Filtrage force en couche service a partir du contexte JWT (module `tenancy`,
  phase 2), jamais d'un parametre client.
- Index composites prefixes par `account_id`.
- Tests anti-fuite cross-tenant : a partir de la phase 2 (acces via service).

---

## 6. Integrite referentielle

- Toutes les tables metier referencent `accounts(id)`.
- `ON DELETE CASCADE` pour les donnees possedees (sensors, readings, alert_rules) ;
  `SET NULL` pour les references historiques (alerts -> rule/sensor).

---

## 7. Migrations

- Outil : Alembic (asynchrone, asyncpg). URL injectee depuis la configuration,
  jamais ecrite dans `alembic.ini`.
- Migration initiale : tables + hypertable + politiques + agregats continus +
  trigger d'audit. Reproductible (downgrade/upgrade verifies).
- Les continuous aggregates sont crees dans un bloc autocommit (ils ne peuvent
  pas s'executer dans une transaction).

```bash
cd backend
alembic upgrade head      # applique
alembic downgrade base    # annule (dev)
```

---

## 8. Contraintes Raspberry Pi 3 (ARM, 1 Go RAM)

Cible de production single-site. Points d'attention :

### 8.1 Architecture ARM
- Utiliser **Raspberry Pi OS 64 bits** : l'image Docker `timescale/timescaledb`
  et les paquets TimescaleDB officiels disposent de builds `arm64`. Eviter le
  32 bits (support partiel, limite memoire par processus).
- Alternative au conteneur : installer TimescaleDB via le depot apt officiel
  directement sur le Pi (empreinte memoire plus faible que Docker).

### 8.2 Reglages faible memoire (1 Go)
Postgres par defaut est trop gourmand. Valeurs de depart pour le Pi :

```
shared_buffers = 128MB
effective_cache_size = 256MB
work_mem = 8MB
maintenance_work_mem = 32MB
max_worker_processes = 4
max_parallel_workers = 2
timescaledb.max_background_workers = 4
```

### 8.3 Carte SD : limiter l'usure et le volume
- La **retention 30 jours** + la **compression** sont ici doublement utiles :
  elles bornent la taille et reduisent les ecritures.
- Prevoir une carte SD endurante (ou un SSD USB) ; sauvegardes hors carte.

### 8.4 Recommandation d'echelle
Pour plusieurs entreprises ou un historique consequent, deporter la plateforme
(API + base + dashboard) sur un serveur central, le Pi ne gardant que le role de
collector (voir README, plan de scalabilite). Le modele de donnees ne change
pas : seule la topologie evolue.
