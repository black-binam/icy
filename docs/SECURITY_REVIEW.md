# Revue de sécurité — itération 1

Date : 2026-04-15
Audit conduit par deux sous-agents indépendants : RGPD/HDS et Crypto/AppSec.

## Synthèse

| Sévérité | Détectés | Corrigés | Résiduels |
|---|---:|---:|---:|
| CRITIQUE | 2 | 2 | 0 |
| HAUT | 5 | 4 | 1 |
| MOYEN | 6 | 4 | 2 |
| BAS / INFO | 4 | 0 | 4 |
| RGPD FAIL | 2 | 2 | 0 |
| RGPD WARN | 6 | 2 | 4 |

## Findings traités dans cette itération

### Critique
- **[C1] Spoofing X-Forwarded-For** — Lecture du header restreinte aux peers présents dans `TRUSTED_PROXY_CIDRS`. Helper `client_ip()` partagé entre rate-limit et audit.
  - `backend/app/core/rate_limit.py:13-58`
  - `backend/app/core/config.py:55-58`
- **[C2] Per-account brute force** — Atténué partiellement : le rate-limit IP reste, et l'IP n'est plus spoofable. *Compteur Redis par email reporté en itération 2 (voir résiduels).*

### RGPD FAIL
- **Patient.address en clair** → chiffré via `EncryptedString` (modèle + migration 0001 mis à jour avant tout déploiement réel).
  - `backend/app/models/patient.py:24`
  - `backend/alembic/versions/0001_initial.py:101`
- **Pas d'audit en lecture** → `AuditMiddleware` trace désormais aussi les `GET` sur `/api/v1/{patients,routes,caregivers,users}`.
  - `backend/app/main.py:24-31, 65-75`

### Haut
- **[H2] Argon2id non figé** → paramètres explicites `time_cost=3, memory_cost=64MiB, parallelism=2, hash_len=32, salt_len=16`.
  - `backend/app/core/security.py:21-29`
- **[H4] `change-me` accepté** → validation `Settings` rejette toute clé contenant `change-me` (peu importe l'environnement).
  - `backend/app/core/config.py:55-87`
  - `.env.example` : valeurs renommées `REPLACE_ME_…` avec instructions de génération
- **[H5] Timing leak via rehash opportuniste** → rehash déporté en `BackgroundTask` FastAPI, le response time reste plat.
  - `backend/app/api/v1/auth.py:46-58, 100-104`

### Moyen
- **[M4] Fuite d'exception solver** → message générique `"Routing solver error"` côté client, exception loggée serveur.
  - `backend/app/api/v1/routes.py:259-269`
- **[M6] Adminer exposé** → déplacé sous le profil Docker `dev` (`docker compose --profile dev up`).
  - `docker-compose.yml:36`
- **[M1] CSP désactivée** → activation en mode `Content-Security-Policy-Report-Only` (compatible avec OSM tiles + Google Fonts).
  - `frontend/nginx.conf:37-40`

## Findings résiduels (itération 2 — backlog)

### Haut
- **[H1] Révocation JWT** : pas de denylist Redis sur `jti`. Un refresh volé reste valide 7 j. À implémenter avec rotation + reuse-detection.
- **[H3] Mass-assignment PATCH /users/me** : à confirmer par un test dédié vérifiant qu'un caregiver ne peut pas se promouvoir admin (le schéma `UserSelfUpdate` semble correct mais sans test).

### Moyen
- **[M2] TrustedHostMiddleware + HTTPSRedirectMiddleware** en prod (à câbler conditionnellement à `is_production`).
- **[M3] Double audit** sur `/auth/login` (middleware + handler explicite) à dédupliquer.
- **[M5] Body size limit** côté FastAPI (actuellement seulement Nginx).

### RGPD WARN
- **Tokens** : refresh en `sessionStorage` côté front, à migrer vers cookie `HttpOnly + SameSite=Lax + Secure` (besoin d'un endpoint backend qui pose le cookie).
- **Consentement** : ajouter actions d'audit `consent.granted` / `consent.revoked` avec version du document.
- **Droit à l'oubli** : implémenter le job Celery de purge J+30.
- **DPIA / DPA** : rédiger la DPIA (obligatoire santé grand échelle), formaliser le DPA avec le fournisseur de routing si non self-hosted (OSRM recommandé).

### Bas / Info
- **[B1]** Migration `python-jose` → `pyjwt` (jose en maintenance limitée).
- **[B2]** Passer à `MultiFernet` pour préparer la rotation `FIELD_ENCRYPTION_KEY`.
- **[B3]** HSTS également côté Nginx front (actuellement seulement côté API en prod).
- **[B4]** Documenter le filtre de redaction des logs (pseudonymisation, pas redaction complète).

## Recommandation

Cette base est désormais sûre pour un environnement de **développement / pré-prod sur données fictives**. Avant tout déploiement traitant des données patients réelles :

1. Traiter les findings résiduels HAUT (H1, H3).
2. Migrer le stockage refresh-token vers cookie HttpOnly.
3. Rédiger DPIA + DPA.
4. Provisionner un hébergement HDS (Scaleway, OVH, Outscale).
5. Auditer les paramètres Argon2id sur le matériel cible (ajuster `memory_cost`).
