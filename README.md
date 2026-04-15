# ICY — Healthcare Route Optimizer

Application web de constitution et de répartition de tournées pour **personnels de santé à domicile**, avec équilibrage de la charge de travail pondérée par pathologie et optimisation du temps de trajet (VRP).

## Fonctionnalités (MVP)

- Gestion utilisateurs (admin, coordinateur, soignant) avec rôles
- Référentiel pathologies avec coefficients de charge configurables
- Fiches patients (adresse géocodée, pathologies, créneaux)
- Fiches soignants (base de départ, capacité journalière)
- Génération automatique de tournées équilibrées (OR-Tools CVRPTW)
- Visualisation carte + timeline, édition drag-and-drop
- Dashboard d'équité des charges
- PWA mobile pour les soignants en tournée

## Stack

| Couche | Technologies |
|---|---|
| Backend | Python 3.11, FastAPI, SQLAlchemy 2, Alembic, Pydantic v2 |
| Base de données | PostgreSQL 16 + PostGIS |
| Tâches async | Celery + Redis |
| Optimisation | Google OR-Tools |
| Routing | OSRM / OpenRouteService / Haversine fallback |
| Frontend | React 18, Vite, TypeScript, Tailwind CSS, shadcn/ui |
| Cartographie | Leaflet + OpenStreetMap |
| Auth | JWT (access/refresh), Argon2id |

## Lancement local

```bash
# 1. Cloner et copier l'environnement
cp .env.example .env

# 2. Lancer les services d'infra
docker compose up -d db redis

# 3. Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:app --reload

# 4. Frontend (autre terminal)
cd frontend
npm install
npm run dev
```

- API : http://localhost:8000/docs
- Front : http://localhost:5173
- Adminer : http://localhost:8080

## RGPD & Sécurité

Voir [`docs/SECURITY.md`](docs/SECURITY.md).

## Suivi du travail

Voir [`TRACKING.md`](TRACKING.md).
