# Conventions de developpement

Regles de travail sur le depot `el-haress-app`. Le depot distant doit rester
propre et professionnel en permanence.

---

## 1. Workflow git

- Depot heberge sur **GitLab**.
- **Jamais de push direct** sur `main` ou `develop`. Ces branches sont protegees
  par le hook `no-commit-to-branch`.
- Chaque phase et sous-phase a sa propre branche.
- **Aucun commit ni push sans confirmation explicite prealable.** Presenter ce
  qui va etre committe/pousse, puis attendre l'accord. L'absence de reponse n'est
  pas un accord.

### Nommage des branches

```
feat/phase-X.Y-nom-sous-phase   sous-phase numerotee
feat/phase-X-nom                phase globale
feat/module-nom                 module fonctionnel complet
fix/nom                         correction ciblee
refactor/nom                    refactorisation
```

Exemples : `feat/phase-0-setup-projet`, `feat/phase-2-auth-tenancy`,
`fix/isolation-account-id`.

### Granularite

Une sous-phase = une branche + un commit + un push. Un commit est atomique : il
fait une seule chose, clairement.

---

## 2. Messages de commit — Conventional Commits

```
feat:      nouvelle fonctionnalite
fix:       correction de bug
docs:      documentation
refactor:  refactorisation sans changement de comportement
test:      ajout ou modification de tests
chore:     maintenance, dependances
perf:      amelioration de performance
style:     formatage uniquement
```

Regles absolues sur les messages :

- Jamais de mention d'un outil ou d'un agent d'assistance.
- Jamais de nom de personne.
- Jamais d'emoji.
- Message factuel, professionnel, en minuscules apres le prefixe.

---

## 3. Standards de code

### Backend (Python)

- Lint et format : **ruff** (`ruff check`, `ruff format`). Zero erreur avant push.
- Validation : **Pydantic v2**, `extra="forbid"` sur tous les schemas.
- SQL : **SQLAlchemy uniquement**, jamais de raw SQL non parametre.
- Logging : **structlog** (JSON). Jamais de `print()` en production.
- IDs : `uuid` partout, jamais d'`int` sequentiel expose.
- Structure de module : `<module>_routes.py`, `<module>_service.py`,
  `<module>_schemas.py`, `<module>_models.py`.

### Frontend (React)

- Lint : **eslint**. Format : **prettier**.
- Pas de `dangerouslySetInnerHTML`.
- Aucune chaine en dur : tout texte via les cles i18n (FR / AR / EN).
- Aucune couleur hex dans un composant : tokens (variables CSS) uniquement.
- Mode clair et sombre, responsive, etats de chargement/erreur/vide geres.

---

## 4. Isolation multi-entreprises (rappel)

- `account_id` **NOT NULL** sur toutes les tables metier.
- L'`account_id` de filtrage vient **toujours** du JWT, jamais d'un parametre
  client.
- Chaque fonctionnalite est couverte par un test anti-fuite cross-tenant.
- Aucune valeur metier en dur (seuils, capteurs, intervalles, destinataires).

---

## 5. Definition de termine

Une tache n'est terminee que lorsque :

- [ ] code fonctionnel, conforme a la structure de module
- [ ] validation Pydantic sur tous les endpoints
- [ ] guards RBAC sur les routes protegees
- [ ] isolation `account_id` appliquee et testee
- [ ] aucune valeur metier en dur
- [ ] tests verts (couverture services >= 80 %)
- [ ] lint sans erreur (ruff / eslint)
- [ ] `.env.example` a jour, aucun secret commite
- [ ] message de commit en Conventional Commits
