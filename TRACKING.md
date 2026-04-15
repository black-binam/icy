# Healthcare Route Optimizer — Suivi de travail

Projet : application web de constitution et de répartition de tournées pour personnels de santé à domicile.
Branche : `claude/healthcare-route-optimizer-HNSTW`

## Stack cible
- **Backend** : FastAPI + SQLAlchemy 2 + Alembic + PostgreSQL/PostGIS + Redis/Celery
- **Frontend** : React + Vite + TypeScript + Tailwind CSS + shadcn/ui + Leaflet
- **Optimisation** : Google OR-Tools (VRP/CVRPTW)
- **Routing routier** : OSRM / OpenRouteService (pluggable)
- **Auth** : JWT (access + refresh), argon2id pour les mots de passe
- **Sécurité/RGPD** : chiffrement au repos des champs sensibles, audit log, minimisation

## Volumes cibles initiaux
- 20 soignants
- 120 patients
- Progressif

## Conventions
- Pas de modification de la DB a posteriori : toute évolution passe par une nouvelle migration Alembic
- Toute donnée de santé considérée comme sensible (chiffrement au repos, logs anonymisés)
- Les mots de passe ne sont JAMAIS en clair ni loggés
- Tests : au minimum 3 itérations de tests fonctionnels avant considéré OK

## Phases

### Phase 1 — Fondations (structure projet) — ✅
- [x] Arborescence backend / frontend / docker
- [x] docker-compose (postgres+postgis, redis, adminer)
- [x] .env.example, .gitignore, README

### Phase 2 — Backend core
- [ ] pyproject.toml + dépendances
- [ ] Configuration (Settings Pydantic, lecture .env)
- [ ] Modèles SQLAlchemy (User, Caregiver, Patient, Pathology, Care, Route, RouteStop, AuditLog)
- [ ] Migrations Alembic initiales
- [ ] Auth JWT (argon2id, tokens)
- [ ] Middleware CORS, rate limit, audit
- [ ] CRUD services

### Phase 3 — Service d'optimisation VRP
- [ ] Adapter routing (OSRM/ORS) avec fallback haversine
- [ ] Solver OR-Tools CVRPTW
- [ ] Pondération par pathologie
- [ ] Équilibrage des charges (variance)
- [ ] Endpoint POST /routes/optimize

### Phase 4 — Frontend
- [ ] Scaffolding Vite + Tailwind + shadcn
- [ ] Auth UI (login, refresh, guards)
- [ ] Layout principal (sidebar, topbar)
- [ ] Dashboard (KPIs, équité des charges)
- [ ] CRUD patients / soignants / pathologies
- [ ] Éditeur de tournées avec carte Leaflet
- [ ] Drag-and-drop entre tournées

### Phase 5 — Tests (3 itérations)
- [ ] Tests unitaires backend (auth, CRUD, VRP)
- [ ] Tests d'intégration API
- [ ] Tests frontend (composants clés)
- [ ] Itération 1, 2, 3

### Phase 6 — Revue sécurité
- [ ] Sous-agent #1 : audit RGPD (minimisation, consentement, droit à l'oubli, chiffrement)
- [ ] Sous-agent #2 : audit cryptographique (hash mdp, JWT, CORS, injections, CSRF, headers)
- [ ] Corrections des findings critiques/hauts

## Journal
- 2026-04-15 : Démarrage, stack validée (FastAPI+React), création structure.
