# Sécurité & RGPD

## Principes

1. **Minimisation** : seules les données strictement nécessaires aux soins sont collectées.
2. **Chiffrement au repos** des champs sensibles (pathologies, notes cliniques, nº sécu si présent) via Fernet (AES-128 CBC + HMAC).
3. **Chiffrement en transit** : TLS obligatoire en production (termination sur reverse proxy).
4. **Hash mots de passe** : Argon2id (OWASP 2023+) — jamais bcrypt seul, jamais MD5/SHA1.
5. **Tokens** : JWT signés HS256 (secret ≥ 64 caractères), access court (15 min), refresh tournant.
6. **Logs** : aucune donnée patient loggée. Audit séparé chiffré.
7. **Droits RGPD** : endpoints `/users/me/export` (portabilité) et `/users/me` DELETE (droit à l'oubli, soft-delete avec purge J+30).
8. **Consentement** : horodatage stocké, traçabilité via `AuditLog`.

## Menaces considérées

| Menace | Contremesure |
|---|---|
| Injection SQL | SQLAlchemy paramétré, pas de f-strings SQL |
| XSS | React échappe par défaut ; CSP stricte ; pas de `dangerouslySetInnerHTML` |
| CSRF | API stateless Bearer JWT, `SameSite=Lax`, pas de cookies d'auth |
| Brute force login | Rate limiting (slowapi), verrouillage progressif, délai aléatoire |
| Enumération comptes | Réponse identique quel que soit l'email |
| Accès horizontal | Vérifs d'ownership dans chaque CRUD |
| Escalade privilèges | RBAC strict (`admin` / `coordinator` / `caregiver`) |
| Fuite via logs | Filtres de redaction (email, tokens, pwd) |
| Secret dans repo | `.env` ignoré, pre-commit `detect-secrets` (à ajouter) |

## Responsabilités hébergeur

Pour la production : **hébergeur certifié HDS** (Scaleway, OVH, Outscale…).
MVP local acceptable uniquement sur données fictives.

## Audit log

Chaque action sensible (login, création patient, accès dossier, modification tournée) génère une entrée `AuditLog` avec :
- `actor_id`, `action`, `target_type`, `target_id`
- `ip_address` tronquée (`/24` IPv4 ou `/48` IPv6) pour pseudonymisation
- `created_at`
- Pas de détails en clair sur les données modifiées
