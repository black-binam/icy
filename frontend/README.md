# ICY — Frontend

Application web React/TypeScript pour la planification et la répartition équitable
de tournées de soins à domicile.

## Stack

- React 18 + Vite + TypeScript strict
- Tailwind CSS (palette teal santé, composants très arrondis)
- shadcn-style primitives (codées dans `src/components/ui/`) avec Radix UI
- React Router v6, TanStack Query v5
- React Hook Form + Zod
- Leaflet + OpenStreetMap via `react-leaflet` (chargé en lazy)
- @dnd-kit pour la réorganisation drag-and-drop des arrêts
- Zustand pour la session (tokens en mémoire)
- vite-plugin-pwa pour l'installation hors-ligne

## Structure

```
src/
  components/
    ui/            # primitives (Button, Card, Dialog, Toast, ...)
    layout/        # AppShell, Sidebar, Topbar
    MapView*.tsx   # carte Leaflet (chargement dynamique)
    WorkloadBadge.tsx
    ProtectedRoute.tsx
  hooks/           # useAuth, useToast
  lib/             # api.ts (Axios), auth.ts (Zustand), utils.ts (cn, formatters)
  pages/           # Login, Dashboard, Patients, Caregivers, Pathologies, Routes, Settings, NotFound
  pwa/             # register service worker
  types/api.ts     # types miroir des schémas backend
  test/setup.ts    # jest-dom hooks
```

## Démarrage local

> Le projet n'est PAS pré-installé. Lancez `npm install` une fois.

```bash
cd frontend
npm install         # installation des dépendances
npm run dev         # serveur Vite sur http://localhost:5173
npm run build       # build prod (sortie ./dist)
npm run preview     # serveur preview du build
npm run lint        # ESLint
npm run typecheck   # tsc --noEmit
npm run test        # vitest
```

Variables d'environnement (préfixe `VITE_` requis) :

- `VITE_API_BASE_URL` — URL de l'API ICY (défaut `http://localhost:8000`)
- `VITE_MAP_TILES_URL` — template OSM (défaut OpenStreetMap public)

## Sécurité

- Les jetons d'accès JWT vivent UNIQUEMENT en mémoire (Zustand). Aucun token n'est
  écrit en `localStorage`. Le refresh token est en `sessionStorage` (cloisonné
  à l'onglet) ; **en production** il doit migrer vers un cookie HttpOnly +
  Secure + SameSite=Lax émis par le backend (cf. `docs/SECURITY.md`).
- Aucun `dangerouslySetInnerHTML` dans le code applicatif.
- Aucun log de token ni de payload `/auth/*` (cf. `src/lib/api.ts`).
- En-têtes de sécurité (X-Frame-Options, X-Content-Type-Options, Referrer-Policy,
  Permissions-Policy, COOP/CORP) servis par Nginx ; CSP fournie commentée prête
  à activer après recensement des domaines.
- TypeScript en mode strict ; utilisation de `any` proscrite sauf justification.

## Docker

Build et exécution :

```bash
docker build -t icy-frontend ./frontend
docker run --rm -p 8080:8080 icy-frontend
```

L'image Nginx s'exécute en utilisateur non-root sur le port 8080 et expose un
endpoint `/healthz`.

## Notes de design

- Composants arrondis (`rounded-xl` / `rounded-2xl`), ombres douces.
- Police Inter (Google Fonts).
- Icônes `lucide-react`.
- Couleur primaire teal `#1f7876` (palette `primary-50` → `primary-900` dans
  `tailwind.config.js`), accents emerald, fond blanc cassé.

## TODO

- Branding : fournir `public/icons/icon-192.png` et `icon-512.png` (cf. README local).
- Activer la CSP de production une fois les domaines API/CDN figés.
- Tests unitaires des composants critiques (WorkloadBadge, MapView mapping).
