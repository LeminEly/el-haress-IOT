# Securite du depot — ce qui ne doit jamais partir au distant

Le depot distant (GitLab) doit rester propre, professionnel et sans aucun secret.
Cette page documente les barrieres en place et ce qu'elles protegent.

---

## 1. Trois barrieres successives

```
1. .gitignore             empeche d'ajouter les fichiers indesirables
2. pre-commit (local)     bloque le commit s'il contient un secret / un defaut
3. GitLab CI (.gitlab-ci) bloque le merge si un secret ou un defaut passe quand meme
```

Aucune de ces barrieres ne se contourne avec `--no-verify`. C'est interdit.

---

## 2. Ce qui ne doit JAMAIS etre versionne

| Categorie                     | Exemples                                              |
| ----------------------------- | ---------------------------------------------------- |
| Secrets / environnement       | `.env`, `.env.*` (sauf `.env.example`)               |
| Cles cryptographiques         | `keys/`, `*.pem`, `*.key`, comptes de service JSON   |
| Donnees reelles (PII)         | `*.xlsx`, `*.csv`, dumps de base                      |
| Artefacts generes             | `node_modules/`, `dist/`, `build/`, `__pycache__/`   |
| Caches d'outils               | `.venv/`, `.pytest_cache/`, `.ruff_cache/`           |
| Logs et bases locales         | `*.log`, `*.sqlite`, `*.db`, `dumps/`, `backups/`    |
| Configs locales personnelles  | `.vscode/*` (sauf fichiers d'equipe), configs d'outils|

Tout cela est couvert par [.gitignore](../.gitignore).

---

## 3. Detection de secrets — gitleaks

[.gitleaks.toml](../.gitleaks.toml) configure la detection de cles API, tokens et
mots de passe en dur. Elle tourne :

- a chaque commit (hook pre-commit) ;
- a chaque pipeline (etape `secrets` de la CI), en bloquant.

Lancer manuellement sur tout le depot :

```bash
gitleaks detect --source . --config .gitleaks.toml --verbose
```

Si un secret a deja ete commite : le **revoquer immediatement** chez le
fournisseur (le retirer de l'historique ne suffit pas, il est compromis), puis
nettoyer l'historique.

---

## 4. Gestion des secrets

- Les secrets vivent uniquement dans `.env` (local) ou dans les variables
  protegees du projet GitLab (CI/CD > Variables) pour le deploiement.
- `.env.example` documente chaque variable avec des valeurs factices.
- Les cles JWT RS256 sont generees localement dans `keys/` (gitignore) et
  injectees par chemin via `.env`.

---

## 5. Hygiene professionnelle du depot

Interdiction totale, partout (code, commits, branches, documentation,
commentaires, configuration) :

- aucune mention d'un outil ou d'un agent d'assistance ;
- aucun nom de personne dans le code ou la documentation technique ;
- aucun emoji.

Le depot doit paraitre entierement ecrit par une equipe humaine senior. Les
fichiers de configuration personnels d'outils d'assistance restent locaux et
sont ignores par git ; on ne doit jamais en ajouter de mention au depot.
