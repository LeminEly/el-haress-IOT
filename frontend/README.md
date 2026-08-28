# Frontend — El-Haress

Tableau de bord de supervision. Vite + React 19 + TypeScript, Tailwind CSS v4 et
shadcn/ui, thematise par les tokens du systeme de design (sombre par defaut),
multilingue FR / AR (RTL) / EN via i18next.

Mise en route detaillee : [../docs/setup-local.md](../docs/setup-local.md).

```bash
npm install
npm run dev            # http://localhost:5173
npm run build          # typecheck + build de production
npm run lint           # eslint
npm run format         # prettier
```

Structure (`src/`) : `i18n/` (FR/AR/EN), `stores/` (theme et langue), `lib/`
(utilitaires), `components/` (dont `ui/` pour shadcn/ui), `styles.css` (tokens du
design system). Les pages et composants metier sont ajoutes en phase 6.
