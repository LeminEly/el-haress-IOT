# Backend — El-Haress

API FastAPI de supervision environnementale multi-entreprises.

Mise en route detaillee : [../docs/setup-local.md](../docs/setup-local.md).

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

uvicorn src.main:app --reload --port 8000   # API + /api/v1/health
ruff check . && ruff format --check .        # lint + format
pytest                                       # tests
```

Structure (`src/`) : `config.py` (parametres typees), `main.py` (bootstrap),
`core/` (logging, exceptions RFC 7807, middleware), `api/` (routes), puis les
modules metier `db/`, `tenancy/`, `auth/`, `sensors/`, `collector/`, `alerting/`,
`notifications/` implementes phase par phase (voir la roadmap).
