# Healthcare Route Optimizer — Suivi de travail

Projet : application web de constitution et de répartition de tournées pour personnels de santé à domicile.
Branche : `claude/healthcare-route-optimizer-HNSTW`

## Stack
- **Backend** : FastAPI + SQLAlchemy 2 + Alembic + PostgreSQL/PostGIS + Redis/Celery
- **Frontend** : React 18 + Vite + TypeScript + Tailwind CSS + shadcn-style + Leaflet
- **Optimisation** : Google OR-Tools (CVRPTW)
- **Routing routier** : OSRM / OpenRouteService (pluggable, fallback Haversine)
- **Auth** : JWT HS256 (access 15 min, refresh 7 j), Argon2id `t=3, m=64MiB, p=2`
- **Sécurité/RGPD** : Fernet `EncryptedString` sur PII patients, audit log avec IP anonymisée, headers HTTP, CSP

## Volumes cibles initiaux
- 20 soignants
- 120 patients
- Progressif

## Conventions
- Pas de modification de la DB a posteriori : toute évolution passe par une nouvelle migration Alembic
- Toute donnée de santé considérée comme sensible (chiffrement au repos, logs anonymisés)
- Les mots de passe ne sont JAMAIS en clair ni loggés
- Tests : 3 itérations minimum avant considéré OK

## Avancement

### ✅ Phase 1 — Fondations
- [x] Arborescence backend / frontend / docker
- [x] docker-compose (postgres+postgis, redis, adminer en profil dev)
- [x] .env.example (avec validations, refus de placeholder), .gitignore, README
- [x] docs/SECURITY.md, docs/ROUTING.md, docs/SECURITY_REVIEW.md

### ✅ Phase 2 — Backend core (FastAPI)
- [x] pyproject.toml avec deps épinglées
- [x] Settings Pydantic (validation `SECRET_KEY`, `FIELD_ENCRYPTION_KEY`, refus de `change-me`)
- [x] Modèles : User, Caregiver, Patient (PII chiffrées), Pathology, PatientPathology, Route, RouteStop, AuditLog
- [x] Migration Alembic 0001 initiale
- [x] Auth JWT (Argon2id figé, refresh, rate-limit, mitigation timing/énumération)
- [x] Middlewares : CORS, SlowAPI, headers sécurité (XCTO/XFO/Referrer/HSTS-prod), audit
- [x] CRUD : patients, caregivers, pathologies, users, routes
- [x] Endpoint POST /routes/optimize → service VRP

### ✅ Phase 3 — Service d'optimisation VRP
- [x] Pluggable distance providers (Haversine / OSRM / OpenRouteService)
- [x] OR-Tools CVRPTW (multi-depot, dimensions Distance/Time/Workload)
- [x] Pondération par pathologie
- [x] Équilibrage des charges (`SetGlobalSpanCostCoefficient`)
- [x] Disjunctions (drop patient si infaisable) → `unassigned`
- [x] docs/ROUTING.md

### ✅ Phase 4 — Frontend React
- [x] Vite + TS + Tailwind + shadcn-style
- [x] Auth (Zustand, intercepteur axios single-flight refresh)
- [x] Layout : Sidebar, Topbar, AppShell
- [x] Pages : Login, Dashboard, Patients, Caregivers, Pathologies, Routes (carte + DnD), Settings, NotFound
- [x] MapView Leaflet (lazy, Suspense)
- [x] PWA (vite-plugin-pwa, manifest, SW)
- [x] Dockerfile + nginx.conf (headers sécurité + CSP Report-Only)

### ✅ Phase 5 — Tests fonctionnels (3 itérations)
- [x] 31 tests : auth (8), patients (5), routing (12), security (6)
- [x] Itération 1 : OK après fix `email-validator`+`slowapi headers`+`reset DB tables`
- [x] Itération 2 : 31/31 OK
- [x] Itération 3 : 31/31 OK
- [x] Frontend : `tsc --noEmit` OK, `vite build` OK

### ✅ Phase 6 — Revue sécurité (1ère itération)
- [x] Sous-agent #1 : audit RGPD/HDS — 12 OK / 6 WARN / 2 FAIL
- [x] Sous-agent #2 : audit Crypto/AppSec — 2 CRITIQUE / 5 HAUT / 6 MOYEN / 4 BAS
- [x] Correctifs critiques/hauts appliqués (XFF spoofing, Argon2 figé, address chiffré, change-me check, timing rehash, exception leak, Adminer profil dev, CSP)
- [x] Re-tests post-correctifs : 31/31 sur 3 itérations
- [x] Documentation des findings résiduels → `docs/SECURITY_REVIEW.md`

## Backlog (itération 2)

Voir `docs/SECURITY_REVIEW.md` section "Findings résiduels".

Top priorités :
1. Révocation JWT (denylist Redis sur `jti`, rotation refresh-token)
2. Test mass-assignment `PATCH /users/me`
3. Refresh-token en cookie `HttpOnly + SameSite=Lax + Secure`
4. Compteur d'échecs login par email (Redis backoff)
5. Job Celery de purge J+30 (soft-delete users + patients)
6. Actions d'audit `consent.granted` / `consent.revoked`
7. `TrustedHostMiddleware` + `HTTPSRedirectMiddleware` en prod
8. DPIA + DPA (formalisation RGPD)

## Journal
- 2026-04-15 — Démarrage projet, validation stack (FastAPI + React).
- 2026-04-15 — Délégation 3 sous-agents en parallèle (backend, frontend, VRP).
- 2026-04-15 — Backend, VRP, frontend complets ; intégration testée.
- 2026-04-15 — 3 itérations de tests fonctionnels backend (31/31).
- 2026-04-15 — Revue sécurité par 2 sous-agents (RGPD, Crypto). Findings critiques/hauts traités. Re-test 3 itérations OK.
